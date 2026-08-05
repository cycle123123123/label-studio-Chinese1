import i18next from "i18next";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAPI } from "../../providers/ApiProvider";
import { useProject } from "../../providers/ProjectProvider";
import { cn } from "../../utils/bem";

const formatPercent = (value) => `${Number(value ?? 0).toFixed(2)}%`;

const MetricCard = ({ title, value, subtitle }) => {
  return (
    <div className={cn("stats-settings").elem("card").toClassName()}>
      <div className={cn("stats-settings").elem("card-title").toClassName()}>{title}</div>
      <div className={cn("stats-settings").elem("card-value").toClassName()}>{value}</div>
      {subtitle ? <div className={cn("stats-settings").elem("card-subtitle").toClassName()}>{subtitle}</div> : null}
    </div>
  );
};

export const StatisticsSettings = () => {
  const { t } = useTranslation();
  const api = useAPI();
  const { project } = useProject();
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);

  const fetchStats = useCallback(async () => {
    if (!project?.id) return;
    setLoading(true);
    try {
      const response = await api.callApi("projectStats", {
        params: { pk: project.id },
      });
      setStats(response ?? {});
    } finally {
      setLoading(false);
    }
  }, [api, project?.id]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const cards = useMemo(() => {
    const overview = stats?.overview ?? {};
    const assignment = stats?.assignment ?? {};
    const workflow = stats?.workflow ?? {};
    const activity = stats?.activity ?? {};

    return [
      {
        key: "total_tasks",
        title: t("stats_settings.total_tasks", "Total Tasks"),
        value: overview.total_tasks ?? 0,
      },
      {
        key: "completed_tasks",
        title: t("stats_settings.completed_tasks", "Completed Tasks"),
        value: overview.completed_tasks ?? 0,
      },
      {
        key: "pending_tasks",
        title: t("stats_settings.pending_tasks", "Pending Tasks"),
        value: overview.pending_tasks ?? 0,
      },
      {
        key: "completion_rate",
        title: t("stats_settings.completion_rate", "Completion Rate"),
        value: formatPercent(overview.completion_rate),
      },
      {
        key: "assigned_tasks",
        title: t("stats_settings.assigned_tasks", "Assigned Tasks"),
        value: assignment.assigned_tasks ?? 0,
        subtitle: `${t("stats_settings.coverage_rate", "Coverage")}: ${formatPercent(assignment.coverage_rate)}`,
      },
      {
        key: "unassigned_tasks",
        title: t("stats_settings.unassigned_tasks", "Unassigned Tasks"),
        value: assignment.unassigned_tasks ?? 0,
      },
      {
        key: "today_completed",
        title: t("stats_settings.today_completed", "Today Completed"),
        value: activity.today_completed ?? 0,
      },
      {
        key: "workflow_rates",
        title: t("stats_settings.workflow_rates", "Workflow Rates"),
        value: `${t("stats_settings.skip_rate", "Skip")}: ${formatPercent(workflow.skip_rate)}`,
      },
    ];
  }, [stats, t]);

  const trend = stats?.activity?.completion_trend ?? [];
  const maxTrendValue = Math.max(1, ...trend.map((item) => item.count ?? 0));
  const annotators = stats?.annotators ?? [];

  return (
    <div className={cn("stats-settings").toClassName()}>
      <div className={cn("stats-settings").elem("wrapper").toClassName()}>
        <h1>{t("stats_settings.section_title", "Project Statistics")}</h1>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>{t("stats_settings.overview_title", "Overview")}</h3>
          <p className="settings-description">
            {t("stats_settings.overview_desc", "Aggregated metrics for current project progress and workload.")}
          </p>
          <div className={cn("stats-settings").elem("grid").toClassName()}>
            {cards.map((card) => (
              <MetricCard key={card.key} title={card.title} value={card.value} subtitle={card.subtitle} />
            ))}
          </div>
        </div>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>{t("stats_settings.trend_title", "7-Day Completion Trend")}</h3>
          <table className={cn("assignment-settings").elem("table").toClassName()}>
            <thead>
              <tr>
                <th>{t("stats_settings.date_col", "Date")}</th>
                <th>{t("stats_settings.count_col", "Completed")}</th>
                <th>{t("stats_settings.trend_col", "Trend")}</th>
              </tr>
            </thead>
            <tbody>
              {trend.map((item) => (
                <tr key={item.date}>
                  <td>{item.date}</td>
                  <td>{item.count ?? 0}</td>
                  <td>
                    <div className={cn("stats-settings").elem("bar-track").toClassName()}>
                      <div
                        className={cn("stats-settings").elem("bar-fill").toClassName()}
                        style={{ width: `${((item.count ?? 0) / maxTrendValue) * 100}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
              {trend.length === 0 && (
                <tr>
                  <td colSpan={3}>{t("stats_settings.empty", "No data")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>{t("stats_settings.annotator_title", "Annotator Performance")}</h3>
          <table className={cn("assignment-settings").elem("table").toClassName()}>
            <thead>
              <tr>
                <th>{t("stats_settings.actor_col", "Annotator")}</th>
                <th>{t("stats_settings.completed_col", "Completed")}</th>
                <th>{t("stats_settings.skipped_col", "Skipped")}</th>
                <th>{t("stats_settings.skip_rate_col", "Skip Rate")}</th>
              </tr>
            </thead>
            <tbody>
              {annotators.map((item, index) => (
                <tr key={item?.actor?.id ?? `actor-${index}`}>
                  <td>{item?.actor?.display_name ?? "-"}</td>
                  <td>{item.completed ?? 0}</td>
                  <td>{item.skipped ?? 0}</td>
                  <td>{formatPercent(item.skip_rate)}</td>
                </tr>
              ))}
              {annotators.length === 0 && (
                <tr>
                  <td colSpan={4}>{t("stats_settings.empty", "No data")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {loading && <p className="settings-description">{t("stats_settings.loading", "Loading...")}</p>}
      </div>
    </div>
  );
};

StatisticsSettings.menuItem = "stats_settings.menu_title";
StatisticsSettings.path = "/stats";
StatisticsSettings.title = i18next.t("stats_settings.menu_title");
