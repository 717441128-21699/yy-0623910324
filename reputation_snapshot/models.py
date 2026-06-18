from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class Sentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Platform(Enum):
    WEIBO = "weibo"
    DOUBAN = "douban"
    ZHIHU = "zhihu"
    XHS = "xhs"
    DOUYIN = "douyin"
    ALL = "all"


@dataclass
class TrendingWord:
    word: str
    count: int
    growth_rate: float
    is_anomaly: bool = False


@dataclass
class ControversyPoint:
    keyword: str
    mentions: int
    sentiment: Sentiment
    description: str
    spread_potential: float


@dataclass
class AnalysisResult:
    artist_name: str
    discussion_volume: int
    volume_change: float
    sentiment: Sentiment
    sentiment_score: float
    top_trending_words: List[TrendingWord]
    controversy_points: List[ControversyPoint]
    anomaly_words: List[str]
    risk_level: RiskLevel
    risk_score: float
    platform: str
    start_time: datetime
    end_time: datetime
    analyzed_at: datetime = field(default_factory=datetime.now)
    focus_keywords: List[str] = field(default_factory=list)


@dataclass
class Artist:
    name: str
    aliases: List[str] = field(default_factory=list)
    priority: int = 1


@dataclass
class Snapshot:
    id: str
    name: str
    artist_name: str
    analysis_result: AnalysisResult
    created_at: datetime
    notes: str = ""


@dataclass
class BatchScanResult:
    artist: Artist
    analysis_result: AnalysisResult
    risk_level: RiskLevel
    risk_score: float
