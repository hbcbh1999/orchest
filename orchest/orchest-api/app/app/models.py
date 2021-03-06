"""Models for the orchest-api

TODO:
    * Start using declarative base so we don't have to keep repeating
      the primary keys, relationships and foreignkeys.
      https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/mixins.html
    * Possibly add `pipeline_uuid` to the primary key.

"""
# from sqlalchemy.ext.declarative import declared_attr

from app.connections import db


class BaseModel(db.Model):
    # Because the class inherits from `db.Model` SQLAlachemy will try to
    # create the table. ``__abstract__=True`` prevents this.
    __abstract__ = True

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class InteractiveSession(BaseModel):
    __tablename__ = 'interactive_sessions'
    pipeline_uuid = db.Column(
        db.String(36),
        primary_key=True,
    )
    status = db.Column(
        db.String(10),
        primary_key=False,
    )
    # Used to connect to Jupyter notebook server.
    jupyter_server_ip = db.Column(
        db.String(15),
        unique=True,
        nullable=True,
    )  # IPv4
    # Used to connect to Jupyter notebook server.
    notebook_server_info = db.Column(
        db.JSON,
        unique=True,
        nullable=True,
    )
    # Docker container IDs. Used internally to identify the resources of
    # a specific session.
    container_ids = db.Column(
        db.JSON,
        unique=False,
        nullable=True,
    )

    def __repr__(self):
        return f'<Launch {self.pipeline_uuid}>'


class PipelineRun(BaseModel):
    __abstract__ = True

    pipeline_uuid = db.Column(
        db.String(36),
        unique=False,
        nullable=False
    )
    status = db.Column(
        db.String(15),
        unique=False,
        nullable=True
    )

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.run_uuid}>'


class PipelineRunPipelineStep(BaseModel):
    __abstract__ = True

    step_uuid = db.Column(
        db.String(36),
        primary_key=True
    )
    status = db.Column(
        db.String(15),
        unique=False,
        nullable=True
    )
    started_time = db.Column(
        db.DateTime,
        unique=False,
        nullable=True
    )
    finished_time = db.Column(
        db.DateTime,
        unique=False,
        nullable=True
    )

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.run_uuid}.{self.step_uuid}>'


class InteractiveRunPipelineStep(PipelineRunPipelineStep):
    __tablename__ = 'interactive_run_pipeline_steps'

    run_uuid = db.Column(
        db.String(36),
        db.ForeignKey('interactive_runs.run_uuid'),
        primary_key=True
    )


class InteractiveRun(PipelineRun):
    __tablename__ = 'interactive_runs'

    run_uuid = db.Column(
        db.String(36),
        primary_key=True
    )

    pipeline_steps = db.relationship('InteractiveRunPipelineStep', lazy='joined')


class NonInteractiveRun(PipelineRun):
    __tablename__ = 'non_interactive_runs'
    __bind_key__ = 'persistent_db'

    experiment_uuid = db.Column(
        db.String(36),
        db.ForeignKey('experiments.experiment_uuid'),
        primary_key=True
    )
    run_uuid = db.Column(
        db.String(36),
        primary_key=True
    )
    # This run_id is used to identify the pipeline run within the
    # experiment and maintain a consistent ordering.
    pipeline_run_id = db.Column(
        db.Integer,
        unique=False,
        nullable=False,
    )
    started_time = db.Column(
        db.DateTime,
        unique=False,
        nullable=True
    )
    finished_time = db.Column(
        db.DateTime,
        unique=False,
        nullable=True
    )

    pipeline_steps = db.relationship('NonInteractiveRunPipelineStep', lazy='joined')


class NonInteractiveRunPipelineStep(PipelineRunPipelineStep):
    __tablename__ = 'non_interactive_run_pipeline_steps'
    __bind_key__ = 'persistent_db'

    experiment_uuid = db.Column(
        db.String(36),
        db.ForeignKey('experiments.experiment_uuid'),
        primary_key=True
    )
    run_uuid = db.Column(
        db.String(36),
        db.ForeignKey('non_interactive_runs.run_uuid'),
        primary_key=True
    )


class Experiment(BaseModel):
    __tablename__ = 'experiments'
    __bind_key__ = 'persistent_db'

    experiment_uuid = db.Column(
        db.String(36),
        primary_key=True
    )
    pipeline_uuid = db.Column(
        db.String(36),
        primary_key=False
    )
    scheduled_start = db.Column(
        db.DateTime,
        nullable=False
    )

    pipeline_runs = db.relationship('NonInteractiveRun', lazy='joined')

    def __repr__(self):
        return f'<Experiment: {self.experiment_uuid}>'
