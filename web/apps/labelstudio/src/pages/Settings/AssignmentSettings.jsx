import { Button } from "@humansignal/ui";
import i18next from "i18next";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useAPI } from "../../providers/ApiProvider";
import { useProject } from "../../providers/ProjectProvider";
import { cn } from "../../utils/bem";

export const AssignmentSettings = () => {
  const { t } = useTranslation();
  const api = useAPI();
  const { project } = useProject();
  const [members, setMembers] = useState([]);
  const [canManage, setCanManage] = useState(false);
  const [assignee, setAssignee] = useState("0");
  const [taskIdsInput, setTaskIdsInput] = useState("");
  const [assignments, setAssignments] = useState([]);
  const [assignmentCount, setAssignmentCount] = useState(0);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditCount, setAuditCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const normalizedTaskIds = useMemo(() => {
    const ids = (taskIdsInput || "")
      .split(/[\s,]+/)
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0);
    return [...new Set(ids)];
  }, [taskIdsInput]);

  const fetchAssignments = useCallback(async () => {
    if (!project?.id) return;
    const response = await api.callApi("projectAssignments", {
      params: { pk: project.id, page: 1, page_size: 50 },
    });
    setAssignments(response?.results ?? []);
    setAssignmentCount(response?.count ?? 0);
    setMembers(response?.members ?? []);
    setCanManage(Boolean(response?.can_manage));
  }, [api, project?.id]);

  const fetchAuditLogs = useCallback(async () => {
    if (!project?.id) return;
    const response = await api.callApi("projectAssignmentAudit", {
      params: { pk: project.id, page: 1, page_size: 50 },
    });
    setAuditLogs(response?.results ?? []);
    setAuditCount(response?.count ?? 0);
  }, [api, project?.id]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      await Promise.all([fetchAssignments(), fetchAuditLogs()]);
    } finally {
      setLoading(false);
    }
  }, [fetchAssignments, fetchAuditLogs]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const applyAssignment = async () => {
    if (!project?.id || normalizedTaskIds.length === 0) return;

    setLoading(true);
    setMessage("");
    try {
      const response = await api.callApi("updateProjectAssignments", {
        params: { pk: project.id },
        body: {
          assignee: Number(assignee),
          task_ids: normalizedTaskIds,
        },
      });
      setMessage(response?.detail ?? t("assignment_settings.operation_done", "Operation completed"));
      setTaskIdsInput("");
      await Promise.all([fetchAssignments(), fetchAuditLogs()]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={cn("assignment-settings").toClassName()}>
      <div className={cn("assignment-settings").elem("wrapper").toClassName()}>
        <h1>{t("assignment_settings.section_title", "Assignment Management")}</h1>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>{t("assignment_settings.bulk_title", "Bulk Assign / Unassign")}</h3>
          <p className="settings-description">
            {t(
              "assignment_settings.bulk_desc",
              "Input task IDs separated by comma or spaces, then select one assignee.",
            )}
          </p>
          <div className={cn("assignment-settings").elem("controls").toClassName()}>
            <select value={assignee} onChange={(event) => setAssignee(event.target.value)} disabled={!canManage || loading}>
              <option value="0">{t("assignment_settings.unassigned", "Unassigned")}</option>
              {members.map((member) => (
                <option key={member.id} value={String(member.id)}>
                  {member.display_name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={taskIdsInput}
              onChange={(event) => setTaskIdsInput(event.target.value)}
              placeholder={t("assignment_settings.task_ids_placeholder", "e.g. 12, 13, 20")}
              disabled={!canManage || loading}
            />
            <Button
              onClick={applyAssignment}
              disabled={!canManage || loading || normalizedTaskIds.length === 0}
              aria-label={t("assignment_settings.apply_aria", "Apply assignment")}
            >
              {t("assignment_settings.apply", "Apply")}
            </Button>
          </div>
          {!canManage && (
            <p className="settings-description">
              {t("assignment_settings.permission_hint", "Only project owner can manage task assignment.")}
            </p>
          )}
          {message && <p className={cn("assignment-settings").elem("message").toClassName()}>{message}</p>}
        </div>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>{t("assignment_settings.current_title", "Current Assignment Records")} ({assignmentCount})</h3>
          <table className={cn("assignment-settings").elem("table").toClassName()}>
            <thead>
              <tr>
                <th>{t("assignment_settings.task_col", "Task")}</th>
                <th>{t("assignment_settings.assignee_col", "Assignee")}</th>
                <th>{t("assignment_settings.assigned_by_col", "Assigned By")}</th>
                <th>{t("assignment_settings.assigned_at_col", "Assigned At")}</th>
              </tr>
            </thead>
            <tbody>
              {assignments.map((item) => (
                <tr key={`${item.task_id}-${item.assigned_at}`}>
                  <td>#{item.task_id}</td>
                  <td>{item?.assignee?.display_name ?? "-"}</td>
                  <td>{item?.assigned_by?.display_name ?? "-"}</td>
                  <td>{item?.assigned_at ? new Date(item.assigned_at).toLocaleString() : "-"}</td>
                </tr>
              ))}
              {assignments.length === 0 && (
                <tr>
                  <td colSpan={4}>{t("assignment_settings.empty", "No records")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className={cn("settings-wrapper").toClassName()}>
          <h3>{t("assignment_settings.audit_title", "Audit Logs")} ({auditCount})</h3>
          <table className={cn("assignment-settings").elem("table").toClassName()}>
            <thead>
              <tr>
                <th>{t("assignment_settings.task_col", "Task")}</th>
                <th>{t("assignment_settings.action_col", "Action")}</th>
                <th>{t("assignment_settings.from_col", "From")}</th>
                <th>{t("assignment_settings.to_col", "To")}</th>
                <th>{t("assignment_settings.by_col", "By")}</th>
                <th>{t("assignment_settings.time_col", "Time")}</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map((item) => (
                <tr key={item.id}>
                  <td>#{item.task_id}</td>
                  <td>{item.action}</td>
                  <td>{item?.previous_assignee?.display_name ?? "-"}</td>
                  <td>{item?.assignee?.display_name ?? "-"}</td>
                  <td>{item?.assigned_by?.display_name ?? "-"}</td>
                  <td>{item?.created_at ? new Date(item.created_at).toLocaleString() : "-"}</td>
                </tr>
              ))}
              {auditLogs.length === 0 && (
                <tr>
                  <td colSpan={6}>{t("assignment_settings.empty", "No records")}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

AssignmentSettings.menuItem = "assignment_settings.menu_title";
AssignmentSettings.path = "/assignment";
AssignmentSettings.title = i18next.t("assignment_settings.menu_title");
