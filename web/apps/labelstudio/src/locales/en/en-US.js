// D:\label-studio\web\apps\labelstudio\src\locales\en-US.js

// 1. 定义翻译对象
export const TRANSLATIONS_EN = {
  // Common terms
  cancel: "Cancel",
  save: "Save",
  common: {
    workspace: "Workspace",
    select_option: "Select an option",
    workspace_description: "Simplify project management by organizing projects into workspaces.",
    learn_more: "Learn more",
  },
  assignment_settings: {
    menu_title: "Assignment",
    section_title: "Assignment Management",
    bulk_title: "Bulk Assign / Unassign",
    bulk_desc: "Input task IDs separated by comma or spaces, then select one assignee.",
    unassigned: "Unassigned",
    task_ids_placeholder: "e.g. 12, 13, 20",
    apply: "Apply",
    apply_aria: "Apply assignment",
    operation_done: "Operation completed",
    permission_hint: "Only project owner can manage task assignment.",
    current_title: "Current Assignment Records",
    audit_title: "Audit Logs",
    task_col: "Task",
    assignee_col: "Assignee",
    assigned_by_col: "Assigned By",
    assigned_at_col: "Assigned At",
    action_col: "Action",
    from_col: "From",
    to_col: "To",
    by_col: "By",
    time_col: "Time",
    empty: "No records",
  },
  workflow_audit_settings: {
    menu_title: "Workflow Audit",
    section_title: "Workflow Audit",
    filter_title: "Filters",
    filter_desc: "Filter by action type, annotator, and time range.",
    all_actions: "All Actions",
    all_members: "All Members",
    action_skipped: "Skipped",
    action_empty: "Empty Submitted",
    apply_filters: "Apply Filters",
    export_csv: "Export CSV",
    list_title: "Audit Records",
    task_col: "Task ID",
    action_col: "Action",
    reason_col: "Reason",
    actor_col: "Actor",
    time_col: "Time",
    empty: "No records",
  },
  stats_settings: {
    menu_title: "Statistics",
    section_title: "Project Statistics",
    overview_title: "Overview",
    overview_desc: "Aggregated metrics for current project progress and workload.",
    total_tasks: "Total Tasks",
    completed_tasks: "Completed Tasks",
    pending_tasks: "Pending Tasks",
    completion_rate: "Completion Rate",
    assigned_tasks: "Assigned Tasks",
    unassigned_tasks: "Unassigned Tasks",
    coverage_rate: "Coverage",
    today_completed: "Today Completed",
    workflow_rates: "Workflow Rates",
    skip_rate: "Skip",
    empty_rate: "Empty",
    trend_title: "7-Day Completion Trend",
    date_col: "Date",
    count_col: "Count",
    trend_col: "Trend",
    annotator_title: "Annotator Performance",
    actor_col: "Annotator",
    completed_col: "Completed",
    skipped_col: "Skipped",
    empty_submitted_col: "Empty Tasks",
    skip_rate_col: "Skip Rate",
    empty_rate_col: "Empty Rate",
    skip_reason_title: "Top Skip Reasons",
    reason_col: "Reason",
    empty: "No data",
    loading: "Loading...",
  },

  // Page translations
  pages: {
    create_project: {
      title: "Create Project",
      steps: {
        name: "Project Name",
        import: "Data Import",
        config: "Labeling Setup",
      },
      project_name: {
        name_title: "Project Name",
        description_title: "Description",
        description_placeholder: "Optional description of your project",
      }
    }
  }
};

// 2. Export in i18next format
export const en_US = {
  translation: TRANSLATIONS_EN,
};
