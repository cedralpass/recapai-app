from datetime import datetime
from typing import Optional, TypedDict


class ArticleData(TypedDict):
    id: int
    title: str
    summary: str
    category: str
    key_topics: list[str]
    url_path: str
    is_read: bool
    embedding: Optional[list]


class Cluster(TypedDict):
    label: str
    articles: list[ArticleData]
    narrative: str


class SynthesisState(TypedDict):
    # Set by the RQ task before graph invocation
    user_id: int
    user_email: str
    user_name: str
    week_start: datetime
    week_end: datetime

    # Populated by gather
    articles: list[ArticleData]

    # Populated by assess
    clustering_strategy: str
    skip_reason: Optional[str]

    # Populated by cluster
    clusters: list[Cluster]

    # Populated by quality_check
    retry_count: int
    quality_verdict: str
    quality_notes: str

    # Populated by compose
    digest_html: str
    digest_text: str

    # Populated by send_email
    sent: bool
    sent_at: Optional[datetime]

    # Set by the RQ task — controls behaviour without changing graph structure
    send_email_flag: bool
    run_id: Optional[int]
