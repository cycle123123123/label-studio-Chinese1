import { observer } from "mobx-react";
import { IconRedo, IconRemove, IconUndo } from "@humansignal/icons";
import { Button } from "@humansignal/ui";
import { useTranslation } from "react-i18next";
import { cn } from "../../utils/bem";
import "./HistoryActions.scss";

export const EditingHistory = observer(({ entity }) => {
  const { t } = useTranslation();
  const { history } = entity;

  return (
    <div className={cn("history-buttons").toClassName()}>
      <Button
        variant="neutral"
        look="string"
        aria-label={t("lsf.history_actions.undo", "Undo")}
        className="!p-0"
        tooltip={t("lsf.history_actions.undo", "Undo")}
        disabled={!history?.canUndo}
        onClick={() => entity.undo()}
      >
        <IconUndo />
      </Button>
      <Button
        variant="neutral"
        look="string"
        aria-label={t("lsf.history_actions.redo", "Redo")}
        className="!p-0"
        tooltip={t("lsf.history_actions.redo", "Redo")}
        disabled={!history?.canRedo}
        onClick={() => entity.redo()}
        leading={<IconRedo />}
      />
      <Button
        look="string"
        variant="negative"
        aria-label={t("lsf.history_actions.reset", "Reset")}
        tooltip={t("lsf.history_actions.reset", "Reset")}
        className="!p-0"
        disabled={!history?.canUndo}
        onClick={() => history?.reset()}
        leading={<IconRemove />}
      />
    </div>
  );
});
