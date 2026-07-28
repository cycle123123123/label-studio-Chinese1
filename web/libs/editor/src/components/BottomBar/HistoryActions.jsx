import { observer } from "mobx-react";
import { IconRedo, IconRemove, IconUndo } from "@humansignal/icons";
import { Tooltip, Button, Space } from "@humansignal/ui";
import { useTranslation } from "react-i18next";
import "./HistoryActions.scss";

export const EditingHistory = observer(({ entity }) => {
  const { t } = useTranslation();
  const { history } = entity;

  return (
    <Space size="small">
      <Tooltip title={t("lsf.history_actions.undo", "Undo")}>
        <Button
          variant="neutral"
          size="small"
          aria-label={t("lsf.history_actions.undo", "Undo")}
          look="string"
          disabled={!history?.canUndo}
          onClick={() => entity.undo()}
          className="!p-0"
        >
          <IconUndo />
        </Button>
      </Tooltip>
      <Tooltip title={t("lsf.history_actions.redo", "Redo")}>
        <Button
          variant="neutral"
          size="small"
          look="string"
          aria-label={t("lsf.history_actions.redo", "Redo")}
          disabled={!history?.canRedo}
          onClick={() => entity.redo()}
          className="!p-0"
        >
          <IconRedo />
        </Button>
      </Tooltip>
      <Tooltip title={t("lsf.history_actions.reset", "Reset")}>
        <Button
          variant="negative"
          look="string"
          size="small"
          aria-label={t("lsf.history_actions.reset", "Reset")}
          disabled={!history?.canUndo}
          onClick={() => history?.reset()}
          className="!p-0"
        >
          <IconRemove />
        </Button>
      </Tooltip>
    </Space>
  );
});
