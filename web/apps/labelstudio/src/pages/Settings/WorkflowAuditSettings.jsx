import { Button } from "@humansignal/ui";
import i18next from "i18next";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAPI } from "../../providers/ApiProvider";
import { useProject } from "../../providers/ProjectProvider";
import { cn } from "../../utils/bem";

export const WorkflowAuditSettings = () => {
  const { t } = useTranslation();
  const api = useAPI();
  const { project } = useProject();
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditCount, setAuditCount] = useState(0);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    action: "",
    actor_id: "",
    date_from: "",
    date_to: "",
  });

  const requestParams = useMemo(() => {
    const params = {
      pk: project?.id,
      page: 1,
      page_size: 100,
    };

    if (filters.action) params.action = filters.action;
    if (filters.actor_id) params.actor_id = Number(filters.actor_id);
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;

    return params;
  }, [filters.action, filters.actor_id, filters.date_from, filters.date_to, project?.id]);

  const fetchAuditLogs = useCallback(async () => {
    if (!project?.id) return;

    setLoading(true);
    try {
      const response = await api.callApi("projectWorkflowAudit", {
        params: requestParams,
      });

      setAuditLogs(response?.results ?? []);
      setAuditCount(response?.count ?? 0);
      setMembers(response?.members ?? []);
    } finally {
      setLoading(false);
    }
  }, [api, project?.id, requestParams]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  const actionDisplay = useCallback(
    (action) => {
      if (action === "submitted") return t("workflow_audit_settings.action_submitted", "Submitted");
      if (action === "skipped") return t("workflow_audit_settings.action_skipped", "Skipped");
      if (action === "empty_submitted") return t("workflow_audit_settings.action_empty", "Empty Submitted");
      return action;
    },
    [t],
  );

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
              <option value="empty_submitted">{t("workflow_audit_settings.action_empty", "Empty Submitted")}</option>
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

            <Button onClick={fetchAuditLogs} disabled={loading}>
              {t("workflow_audit_settings.apply_filters", "Apply Filters")}
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
                <th>{t("workflow_audit_settings.reason_col", "Reason")}</th>
                <th>{t("workflow_audit_settings.actor_col", "Actor")}</th>
                <th>{t("workflow_audit_settings.time_col", "Time")}</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((item) => (
                <tr key={item.id}>
                  <td>#{item.task_id}</td>
                  <td>{actionDisplay(item.action)}</td>
                  <td>{item.reason || "-"}</td>
                  <td>{item?.actor?.display_name ?? "-"}</td>
                  <td>{item?.created_at ? new Date(item.created_at).toLocaleString() : "-"}</td>
                </tr>
              ))}
              {auditLogs.length === 0 && (
                <tr>
                  <td colSpan={5}>{t("workflow_audit_settings.empty", "No records")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

WorkflowAuditSettings.menuItem = "workflow_audit_settings.menu_title";
WorkflowAuditSettings.path = "/workflow-audit";
WorkflowAuditSettings.title = i18next.t("workflow_audit_settings.menu_title");
