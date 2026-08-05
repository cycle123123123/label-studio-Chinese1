import { useTranslation } from "react-i18next"; // 1. 在这里导入 hook
import { SidebarMenu } from "../../components/SidebarMenu/SidebarMenu";
import { useProject } from "../../providers/ProjectProvider";
import { WebhookPage } from "../WebhookPage/WebhookPage";
import { DangerZone } from "./DangerZone";
import { GeneralSettings } from "./GeneralSettings";
import { AnnotationSettings } from "./AnnotationSettings";
import { LabelingSettings } from "./LabelingSettings";
import { AssignmentSettings } from "./AssignmentSettings";
import { WorkflowAuditSettings } from "./WorkflowAuditSettings";
import { StatisticsSettings } from "./StatisticsSettings";
import { MachineLearningSettings } from "./MachineLearningSettings/MachineLearningSettings";
import { PredictionsSettings } from "./PredictionsSettings/PredictionsSettings";
import { StorageSettings } from "./StorageSettings/StorageSettings";
import "./settings.scss";

export const MenuLayout = ({ children, ...routeProps }) => {
  const { project } = useProject();
  const canManageAssignments = Boolean(project?.assignment_settings?.can_manage);
  const { t } = useTranslation(); // 2. 在这里安全地获取 t 函数

  return (
    <SidebarMenu
      menuItems={[
        GeneralSettings,
        LabelingSettings,
        canManageAssignments && AssignmentSettings,
        canManageAssignments && WorkflowAuditSettings,
        canManageAssignments && StatisticsSettings,
        AnnotationSettings,
        MachineLearningSettings,
        PredictionsSettings,
        StorageSettings,
        WebhookPage,
        DangerZone,
      ].filter(Boolean)}
      path={routeProps.match.url}
      children={children}
      t={t} // 3. 将获取到的 t 函数作为 prop 传递下去
    />
  );
};

const pages = {
  AnnotationSettings,
  LabelingSettings,
  AssignmentSettings,
  WorkflowAuditSettings,
  StatisticsSettings,
  MachineLearningSettings,
  PredictionsSettings,
  StorageSettings,
  WebhookPage,
  DangerZone,
};

export const SettingsPage = {
  title: "Settings", // 建议也将这个改为翻译键，如 "settings_page_title"
  path: "/settings",
  exact: true,
  layout: MenuLayout,
  component: GeneralSettings,
  pages,
};
