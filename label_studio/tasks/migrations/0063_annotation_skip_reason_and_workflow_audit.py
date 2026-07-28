from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0034_project_require_comment_on_skip'),
        ('tasks', '0062_rename_taskassignment_index_names'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='annotation',
            name='is_empty_submission',
            field=models.BooleanField(
                default=False,
                help_text='True when annotation was submitted without any result regions',
                verbose_name='is empty submission',
            ),
        ),
        migrations.AddField(
            model_name='annotation',
            name='skip_reason',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Reason provided by annotator when skipping task',
                null=True,
                verbose_name='skip reason',
            ),
        ),
        migrations.AddIndex(
            model_name='annotation',
            index=models.Index(fields=['is_empty_submission'], name='task_comple_is_empt_b0c283_idx'),
        ),
        migrations.CreateModel(
            name='TaskWorkflowAuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'action',
                    models.CharField(
                        choices=[('skipped', 'Skipped'), ('empty_submitted', 'Empty Submitted')],
                        help_text='Workflow action type',
                        max_length=32,
                    ),
                ),
                (
                    'reason',
                    models.TextField(
                        blank=True,
                        default='',
                        help_text='Optional reason for workflow action, e.g. skip reason',
                        null=True,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Creation time', verbose_name='created at')),
                (
                    'actor',
                    models.ForeignKey(
                        blank=True,
                        help_text='User who performed workflow action',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='task_workflow_audit_as_actor',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'annotation',
                    models.ForeignKey(
                        blank=True,
                        help_text='Annotation associated with workflow action',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='workflow_audit_logs',
                        to='tasks.annotation',
                    ),
                ),
                (
                    'project',
                    models.ForeignKey(
                        help_text='Project of workflow action',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='task_workflow_audit_logs',
                        to='projects.project',
                    ),
                ),
                (
                    'task',
                    models.ForeignKey(
                        help_text='Task affected by workflow action',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='workflow_audit_logs',
                        to='tasks.task',
                    ),
                ),
            ],
            options={
                'db_table': 'task_workflow_audit_log',
            },
        ),
        migrations.AddIndex(
            model_name='taskworkflowauditlog',
            index=models.Index(fields=['project', '-created_at'], name='task_workfl_project_5f29f5_idx'),
        ),
        migrations.AddIndex(
            model_name='taskworkflowauditlog',
            index=models.Index(fields=['task', '-created_at'], name='task_workfl_task_id_a79394_idx'),
        ),
        migrations.AddIndex(
            model_name='taskworkflowauditlog',
            index=models.Index(fields=['actor', '-created_at'], name='task_workfl_actor_i_ec4bb1_idx'),
        ),
    ]
