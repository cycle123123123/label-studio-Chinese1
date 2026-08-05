import { Button } from "@humansignal/ui";
import i18next from "i18next";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAPI } from "../../providers/ApiProvider";
import { useProject } from "../../providers/ProjectProvider";
import { cn } from "../../utils/bem";
import { Pagination } from "../../components/Pagination/Pagination";
import { absoluteURL } from "../../utils/helpers";

const PAGE_SIZE = 100;

export const WorkflowAuditSettings = () => {
  const { t } = useTranslation();
  const api = useAPI();
  const { project } = useProject();
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditCount, setAuditCount] = useState(0);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    action: "",
    actor_id: "",
    date_from: "",
    date_to: "",
  });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const requestSequence = useRef(0);

  const requestParams = useMemo(() => {
    const params = {
      pk: project?.id,
      page,
      page_size: PAGE_SIZE,
    };

    if (appliedFilters.action) params.action = appliedFilters.action;
    if (appliedFilters.actor_id) params.actor_id = Number(appliedFilters.actor_id);
    if (appliedFilters.date_from) params.date_from = appliedFilters.date_from;
    if (appliedFilters.date_to) params.date_to = appliedFilters.date_to;

    return params;
  }, [appliedFilters, page, project?.id]);

  const fetchAuditLogs = useCallback(
    async (params = requestParams) => {
      if (!project?.id) return;

      const requestId = ++requestSequence.current;
      setLoading(true);
      try {
        const response = await api.callApi("projectWorkflowAudit", {
          params,
        });
        if (!response || requestId !== requestSequence.current) return;

        setAuditLogs(response?.results ?? []);
        setAuditCount(response?.count ?? 0);
        setMembers(response?.members ?? []);
      } finally {
        if (requestId === requestSequence.current) setLoading(false);
      }
    },
    [api, project?.id, requestParams],
  );

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  const actionDisplay = useCallback(
    (action) => {
      if (action === "submitted") return t("workflow_audit_settings.action_submitted", "Submitted");
      if (action === "skipped") return t("workflow_audit_settings.action_skipped", "Skipped");
      return action;
    },
    [t],
  );

  const applyFilters = useCallback(() => {
    setPage(1);
    setAppliedFilters(filters);
  }, [filters]);

  const exportCsv = useCallback(() => {
    if (!project?.id) return;

    const params = new URLSearchParams({ format: "csv" });
    if (filters.action) params.set("action", filters.action);
    if (filters.actor_id) params.set("actor_id", filters.actor_id);
    if (filters.date_from) params.set("date_from", filters.date_from);
    if (filters.date_to) params.set("date_to", filters.date_to);

    window.open(
      absoluteURL(`/api/projects/${project.id}/workflow-audit/?${params.toString()}`),
      "_blank",
      "noopener,noreferrer",
    );
  }, [filters.action, filters.actor_id, filters.date_from, filters.date_to, project?.id]);

  return (
    <div className={cn("assignment-settings").toClassName()}>
      <div className={cn("assignment-settings").elem("wrapper").toClassName()}>
        <h1>{t("workflow_audit_settings.section_title", "Workflow Audit")}</h1>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>{t("workflow_audit_settings.filter_title", "Filters")}</h3>
          <p className="settings-description">
            {t("workflow_audit_settings.filter_desc", "Filter by action type, annotator, and time range.")}
          </p>

          <div className={cn("assignment-settings").elem("controls").toClassName()}>
            <select
              value={filters.action}
              onChange={(event) => setFilters((prev) => ({ ...prev, action: event.target.value }))}
              disabled={loading}
            >
              <option value="">{t("workflow_audit_settings.all_actions", "All Actions")}</option>
              <option value="submitted">{t("workflow_audit_settings.action_submitted", "Submitted")}</option>
              <option value="skipped">{t("workflow_audit_settings.action_skipped", "Skipped")}</option>
            </select>

            <select
              value={filters.actor_id}
              onChange={(event) => setFilters((prev) => ({ ...prev, actor_id: event.target.value }))}
              disabled={loading}
            >
              <option value="">{t("workflow_audit_settings.all_members", "All Members")}</option>
              {members.map((member) => (
                <option key={member.id} value={String(member.id)}>
                  {member.display_name}
                </option>
              ))}
            </select>

            <input
              type="date"
              value={filters.date_from}
              onChange={(event) => setFilters((prev) => ({ ...prev, date_from: event.target.value }))}
              disabled={loading}
            />
          </div>

          <div className={cn("assignment-settings").elem("controls").toClassName()} style={{ marginTop: 8 }}>
            <input
              type="date"
              value={filters.date_to}
              onChange={(event) => setFilters((prev) => ({ ...prev, date_to: event.target.value }))}
              disabled={loading}
            />

            <Button onClick={applyFilters} disabled={loading}>
              {t("workflow_audit_settings.apply_filters", "Apply Filters")}
            </Button>
            <Button onClick={exportCsv} disabled={!project?.id || loading} look="outlined">
              {t("workflow_audit_settings.export_csv", "Export CSV")}
            </Button>
          </div>
        </div>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>
            {t("workflow_audit_settings.list_title", "Audit Records")} ({auditCount})
          </h3>
          <table className={cn("assignment-settings").elem("table").toClassName()}>
            <thead>
              <tr>
                <th>{t("workflow_audit_settings.task_col", "Task ID")}</th>
                <th>{t("workflow_audit_settings.action_col", "Action")}</th>
                <th>{t("workflow_audit_settings.actor_col", "Actor")}</th>
                <th>{t("workflow_audit_settings.time_col", "Time")}</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((item) => (
                <tr key={item.id}>
                  <td>#{item.task_id}</td>
                  <td>{actionDisplay(item.action)}</td>
                  <td>{item?.actor?.display_name ?? "-"}</td>
                  <td>{item?.created_at ? new Date(item.created_at).toLocaleString() : "-"}</td>
                </tr>
              ))}
              {auditLogs.length === 0 && (
                <tr>
                  <td colSpan={4}>{t("workflow_audit_settings.empty", "No records")}</td>
                </tr>
              )}
            </tbody>
          </table>
          <Pagination
            name="project-workflow-audit"
            label={t("workflow_audit_settings.list_title", "Audit Records")}
            page={page}
            totalItems={auditCount}
            totalPages={Math.max(1, Math.ceil(auditCount / PAGE_SIZE))}
            pageSize={PAGE_SIZE}
            disabled={loading}
            onPageLoad={async (nextPage) => setPage(nextPage)}
          />
        </div>
      </div>
    </div>
  );
};

WorkflowAuditSettings.menuItem = "workflow_audit_settings.menu_title";
WorkflowAuditSettings.path = "/workflow-audit";
WorkflowAuditSettings.title = i18next.t("workflow_audit_settings.menu_title");
