"""
MW Design Studio - Advanced Analytics Engine
Comprehensive business intelligence and reporting system
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, desc, asc, and_, or_, case
from collections import defaultdict, Counter
import calendar
import json

from models_v2 import Submission, User

class AnalyticsEngine:
    """Advanced analytics engine for MW Design Studio dashboard"""
    
    def __init__(self, db: Session):
        self.db = db
        self.current_date = datetime.utcnow()
        
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics"""
        return {
            "overview": self.get_overview_metrics(),
            "conversion_funnel": self.get_conversion_funnel(),
            "revenue_analytics": self.get_revenue_analytics(),
            "platform_analytics": self.get_platform_analytics(),
            "timeline_analytics": self.get_timeline_analytics(),
            "lead_quality": self.get_lead_quality_metrics(),
            "team_performance": self.get_team_performance(),
            "forecasting": self.get_forecasting_data()
        }
    
    def get_overview_metrics(self) -> Dict[str, Any]:
        """Get key overview metrics"""
        # Time periods
        today = self.current_date.date()
        yesterday = today - timedelta(days=1)
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        
        # Basic counts
        total_submissions = self.db.query(Submission).count()
        new_submissions = self.db.query(Submission).filter(Submission.status == "New").count()
        contacted_submissions = self.db.query(Submission).filter(Submission.status == "Contacted").count()
        proposal_sent = self.db.query(Submission).filter(Submission.status == "Proposal Sent").count()
        won_submissions = self.db.query(Submission).filter(Submission.status == "Won").count()
        lost_submissions = self.db.query(Submission).filter(Submission.status == "Lost").count()
        
        # This month vs last month
        this_month_submissions = self.db.query(Submission).filter(
            func.date(Submission.created_at) >= this_month_start
        ).count()
        
        last_month_submissions = self.db.query(Submission).filter(
            and_(
                func.date(Submission.created_at) >= last_month_start,
                func.date(Submission.created_at) <= last_month_end
            )
        ).count()
        
        # Calculate growth
        month_growth = self._calculate_growth(this_month_submissions, last_month_submissions)
        
        # Conversion rates
        total_closed = won_submissions + lost_submissions
        conversion_rate = round((won_submissions / total_submissions * 100) if total_submissions > 0 else 0, 1)
        win_rate = round((won_submissions / total_closed * 100) if total_closed > 0 else 0, 1)
        
        # Average time to close
        avg_time_to_close = self._calculate_avg_time_to_close()
        
        return {
            "total_submissions": total_submissions,
            "new_submissions": new_submissions,
            "in_progress": contacted_submissions + proposal_sent,
            "won_submissions": won_submissions,
            "lost_submissions": lost_submissions,
            "conversion_rate": conversion_rate,
            "win_rate": win_rate,
            "month_growth": month_growth,
            "avg_time_to_close": avg_time_to_close,
            "active_pipeline_value": self._calculate_pipeline_value()
        }
    
    def get_conversion_funnel(self) -> Dict[str, Any]:
        """Get detailed conversion funnel analytics"""
        # Get counts for each stage
        stages = ["New", "Contacted", "Proposal Sent", "Won", "Lost"]
        funnel_data = {}
        
        for stage in stages:
            count = self.db.query(Submission).filter(Submission.status == stage).count()
            funnel_data[stage.lower().replace(" ", "_")] = count
        
        # Calculate conversion rates between stages
        total = funnel_data["new"] + funnel_data["contacted"] + funnel_data["proposal_sent"] + funnel_data["won"] + funnel_data["lost"]
        
        conversion_rates = {}
        if total > 0:
            conversion_rates = {
                "new_to_contacted": round((funnel_data["contacted"] + funnel_data["proposal_sent"] + funnel_data["won"]) / total * 100, 1),
                "contacted_to_proposal": round((funnel_data["proposal_sent"] + funnel_data["won"]) / total * 100, 1),
                "proposal_to_won": round(funnel_data["won"] / total * 100, 1)
            }
        
        return {
            "funnel_counts": funnel_data,
            "conversion_rates": conversion_rates,
            "total_leads": total
        }
    
    def get_revenue_analytics(self) -> Dict[str, Any]:
        """Get revenue and budget analytics"""
        # Parse budget ranges and calculate potential revenue
        budget_mapping = {
            "$1,000-5,000": 3000,
            "$5,000-10,000": 7500,
            "$10,000-25,000": 17500,
            "$25,000+": 35000
        }
        
        # Current pipeline value
        pipeline_value = 0
        won_revenue = 0
        lost_revenue = 0
        
        submissions = self.db.query(Submission).all()
        
        budget_distribution = Counter()
        revenue_by_month = defaultdict(int)
        
        for submission in submissions:
            if submission.budget and submission.budget in budget_mapping:
                budget_value = budget_mapping[submission.budget]
                budget_distribution[submission.budget] += 1
                
                if submission.status == "Won":
                    won_revenue += budget_value
                    if submission.created_at:
                        month_key = submission.created_at.strftime("%Y-%m")
                        revenue_by_month[month_key] += budget_value
                elif submission.status == "Lost":
                    lost_revenue += budget_value
                elif submission.status in ["New", "Contacted", "Proposal Sent"]:
                    pipeline_value += budget_value
        
        # Average deal size
        total_won = self.db.query(Submission).filter(Submission.status == "Won").count()
        avg_deal_size = round(won_revenue / total_won) if total_won > 0 else 0
        
        return {
            "pipeline_value": pipeline_value,
            "won_revenue": won_revenue,
            "lost_revenue": lost_revenue,
            "avg_deal_size": avg_deal_size,
            "budget_distribution": dict(budget_distribution),
            "revenue_by_month": dict(revenue_by_month)
        }
    
    def get_platform_analytics(self) -> Dict[str, Any]:
        """Get detailed platform preference analytics"""
        platform_stats = Counter()
        platform_combinations = Counter()
        platform_conversion = defaultdict(lambda: {"total": 0, "won": 0})
        
        submissions = self.db.query(Submission).all()
        
        for submission in submissions:
            if submission.platforms:
                # Individual platform counts
                for platform in submission.platforms:
                    platform_stats[platform] += 1
                    platform_conversion[platform]["total"] += 1
                    if submission.status == "Won":
                        platform_conversion[platform]["won"] += 1
                
                # Platform combinations
                if len(submission.platforms) > 1:
                    combo = " + ".join(sorted(submission.platforms))
                    platform_combinations[combo] += 1
        
        # Calculate conversion rates by platform
        platform_conversion_rates = {}
        for platform, data in platform_conversion.items():
            if data["total"] > 0:
                platform_conversion_rates[platform] = round(data["won"] / data["total"] * 100, 1)
        
        return {
            "platform_counts": dict(platform_stats.most_common()),
            "platform_combinations": dict(platform_combinations.most_common(10)),
            "platform_conversion_rates": platform_conversion_rates,
            "top_platforms": list(platform_stats.most_common(5))
        }
    
    def get_timeline_analytics(self) -> Dict[str, Any]:
        """Get comprehensive timeline analytics"""
        # Daily submissions for last 30 days
        thirty_days_ago = self.current_date - timedelta(days=30)
        
        daily_submissions = self.db.query(
            func.date(Submission.created_at).label('date'),
            func.count(Submission.id).label('count')
        ).filter(
            Submission.created_at >= thirty_days_ago
        ).group_by(
            func.date(Submission.created_at)
        ).order_by('date').all()
        
        # Weekly submissions for last 12 weeks
        twelve_weeks_ago = self.current_date - timedelta(weeks=12)
        
        weekly_submissions = self.db.query(
            func.date_trunc('week', Submission.created_at).label('week'),
            func.count(Submission.id).label('count')
        ).filter(
            Submission.created_at >= twelve_weeks_ago
        ).group_by(
            func.date_trunc('week', Submission.created_at)
        ).order_by('week').all()
        
        # Monthly submissions for last 12 months
        twelve_months_ago = self.current_date - timedelta(days=365)
        
        monthly_submissions = self.db.query(
            func.date_trunc('month', Submission.created_at).label('month'),
            func.count(Submission.id).label('count')
        ).filter(
            Submission.created_at >= twelve_months_ago
        ).group_by(
            func.date_trunc('month', Submission.created_at)
        ).order_by('month').all()
        
        # Hour of day analysis
        hourly_distribution = self.db.query(
            extract('hour', Submission.created_at).label('hour'),
            func.count(Submission.id).label('count')
        ).group_by(
            extract('hour', Submission.created_at)
        ).order_by('hour').all()
        
        # Day of week analysis
        daily_distribution = self.db.query(
            extract('dow', Submission.created_at).label('dow'),
            func.count(Submission.id).label('count')
        ).group_by(
            extract('dow', Submission.created_at)
        ).order_by('dow').all()
        
        return {
            "daily_submissions": [{"date": str(d.date), "count": d.count} for d in daily_submissions],
            "weekly_submissions": [{"week": str(w.week.date() if w.week else ""), "count": w.count} for w in weekly_submissions],
            "monthly_submissions": [{"month": str(m.month.date() if m.month else ""), "count": m.count} for m in monthly_submissions],
            "hourly_distribution": [{"hour": int(h.hour), "count": h.count} for h in hourly_distribution],
            "daily_distribution": [{"day": int(d.dow), "count": d.count} for d in daily_distribution]
        }
    
    def get_lead_quality_metrics(self) -> Dict[str, Any]:
        """Analyze lead quality and scoring"""
        # Lead scoring based on various factors
        high_quality_indicators = {
            "has_website": 0,
            "high_budget": 0,
            "multiple_platforms": 0,
            "immediate_timeline": 0,
            "complete_profile": 0
        }
        
        lead_scores = []
        submissions = self.db.query(Submission).all()
        
        for submission in submissions:
            score = 0
            
            # Website presence
            if submission.website:
                score += 20
                high_quality_indicators["has_website"] += 1
            
            # Budget analysis
            if submission.budget in ["$10,000-25,000", "$25,000+"]:
                score += 30
                high_quality_indicators["high_budget"] += 1
            elif submission.budget in ["$5,000-10,000"]:
                score += 20
            
            # Platform diversity
            if submission.platforms and len(submission.platforms) >= 3:
                score += 25
                high_quality_indicators["multiple_platforms"] += 1
            
            # Timeline urgency
            if submission.timeline in ["Immediately", "Within 1 month"]:
                score += 15
                high_quality_indicators["immediate_timeline"] += 1
            
            # Profile completeness
            completed_fields = sum([
                bool(submission.brand_story),
                bool(submission.usp),
                bool(submission.demographics),
                bool(submission.brand_voice),
                bool(submission.competitors)
            ])
            if completed_fields >= 3:
                score += 10
                high_quality_indicators["complete_profile"] += 1
            
            lead_scores.append({
                "id": submission.id,
                "business_name": submission.business_name,
                "score": score,
                "status": submission.status
            })
        
        # Analyze correlation between score and conversion
        high_score_leads = [l for l in lead_scores if l["score"] >= 70]
        high_score_won = [l for l in high_score_leads if l["status"] == "Won"]
        
        quality_conversion_rate = round(
            len(high_score_won) / len(high_score_leads) * 100
        ) if high_score_leads else 0
        
        return {
            "lead_scores": sorted(lead_scores, key=lambda x: x["score"], reverse=True)[:20],
            "quality_indicators": high_quality_indicators,
            "quality_conversion_rate": quality_conversion_rate,
            "avg_lead_score": round(sum(l["score"] for l in lead_scores) / len(lead_scores)) if lead_scores else 0
        }
    
    def get_team_performance(self) -> Dict[str, Any]:
        """Analyze team performance metrics"""
        # Status change velocity
        status_changes = defaultdict(list)
        
        # This would require tracking status change history
        # For now, we'll simulate with creation to current status time
        submissions = self.db.query(Submission).filter(
            Submission.status.in_(["Won", "Lost"])
        ).all()
        
        resolution_times = []
        for submission in submissions:
            if submission.created_at and submission.updated_at:
                days_to_resolve = (submission.updated_at - submission.created_at).days
                resolution_times.append(days_to_resolve)
                status_changes[submission.status].append(days_to_resolve)
        
        avg_resolution_time = round(sum(resolution_times) / len(resolution_times)) if resolution_times else 0
        
        # Response time analysis (simulated)
        quick_responses = sum(1 for t in resolution_times if t <= 3)  # 3 days or less
        response_rate = round(quick_responses / len(resolution_times) * 100) if resolution_times else 0
        
        return {
            "avg_resolution_time": avg_resolution_time,
            "quick_response_rate": response_rate,
            "status_distribution": {
                "won_avg_time": round(sum(status_changes["Won"]) / len(status_changes["Won"])) if status_changes["Won"] else 0,
                "lost_avg_time": round(sum(status_changes["Lost"]) / len(status_changes["Lost"])) if status_changes["Lost"] else 0
            }
        }
    
    def get_forecasting_data(self) -> Dict[str, Any]:
        """Generate forecasting and trend predictions"""
        # Get last 6 months of data for trend analysis
        six_months_ago = self.current_date - timedelta(days=180)
        
        monthly_data = self.db.query(
            func.date_trunc('month', Submission.created_at).label('month'),
            func.count(Submission.id).label('submissions'),
            func.count(case((Submission.status == 'Won', 1))).label('wins')
        ).filter(
            Submission.created_at >= six_months_ago
        ).group_by(
            func.date_trunc('month', Submission.created_at)
        ).order_by('month').all()
        
        # Simple trend calculation (would be more sophisticated in production)
        if len(monthly_data) >= 3:
            recent_avg = sum(m.submissions for m in monthly_data[-3:]) / 3
            older_avg = sum(m.submissions for m in monthly_data[:-3]) / len(monthly_data[:-3]) if len(monthly_data) > 3 else recent_avg
            
            trend_direction = "up" if recent_avg > older_avg else "down" if recent_avg < older_avg else "stable"
            trend_percentage = round(abs(recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        else:
            trend_direction = "stable"
            trend_percentage = 0
            recent_avg = 0
        
        # Forecast next month (simple projection)
        forecast_next_month = round(recent_avg * (1.1 if trend_direction == "up" else 0.9 if trend_direction == "down" else 1))
        
        return {
            "trend_direction": trend_direction,
            "trend_percentage": trend_percentage,
            "forecast_next_month": forecast_next_month,
            "monthly_trend_data": [
                {
                    "month": str(m.month.date() if m.month else ""),
                    "submissions": m.submissions,
                    "wins": m.wins
                } for m in monthly_data
            ]
        }
    
    def _calculate_growth(self, current: int, previous: int) -> Dict[str, Any]:
        """Calculate growth percentage and direction"""
        if previous == 0:
            return {"percentage": 0, "direction": "stable", "absolute": current}
        
        percentage = round((current - previous) / previous * 100, 1)
        direction = "up" if percentage > 0 else "down" if percentage < 0 else "stable"
        
        return {
            "percentage": abs(percentage),
            "direction": direction,
            "absolute": current - previous
        }
    
    def _calculate_avg_time_to_close(self) -> int:
        """Calculate average time from submission to close"""
        closed_submissions = self.db.query(Submission).filter(
            Submission.status.in_(["Won", "Lost"]),
            Submission.updated_at.isnot(None)
        ).all()
        
        if not closed_submissions:
            return 0
        
        total_days = sum(
            (sub.updated_at - sub.created_at).days
            for sub in closed_submissions
            if sub.created_at and sub.updated_at
        )
        
        return round(total_days / len(closed_submissions))
    
    def _calculate_pipeline_value(self) -> int:
        """Calculate total value of active pipeline"""
        budget_mapping = {
            "$1,000-5,000": 3000,
            "$5,000-10,000": 7500,
            "$10,000-25,000": 17500,
            "$25,000+": 35000
        }
        
        active_submissions = self.db.query(Submission).filter(
            Submission.status.in_(["New", "Contacted", "Proposal Sent"])
        ).all()
        
        total_value = 0
        for submission in active_submissions:
            if submission.budget and submission.budget in budget_mapping:
                total_value += budget_mapping[submission.budget]
        
        return total_value

    def get_custom_date_range_analytics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get analytics for a custom date range"""
        submissions = self.db.query(Submission).filter(
            and_(
                func.date(Submission.created_at) >= start_date,
                func.date(Submission.created_at) <= end_date
            )
        ).all()
        
        # Analyze the filtered data
        total = len(submissions)
        won = len([s for s in submissions if s.status == "Won"])
        lost = len([s for s in submissions if s.status == "Lost"])
        
        conversion_rate = round(won / total * 100) if total > 0 else 0
        
        # Platform analysis for date range
        platform_stats = Counter()
        for submission in submissions:
            if submission.platforms:
                for platform in submission.platforms:
                    platform_stats[platform] += 1
        
        return {
            "date_range": {
                "start": str(start_date),
                "end": str(end_date)
            },
            "totals": {
                "submissions": total,
                "won": won,
                "lost": lost,
                "conversion_rate": conversion_rate
            },
            "platform_breakdown": dict(platform_stats),
            "daily_breakdown": self._get_daily_breakdown(submissions, start_date, end_date)
        }
    
    def _get_daily_breakdown(self, submissions: List[Submission], start_date: date, end_date: date) -> List[Dict]:
        """Get daily breakdown for submissions in date range"""
        daily_counts = defaultdict(int)
        
        for submission in submissions:
            if submission.created_at:
                day = submission.created_at.date()
                daily_counts[day] += 1
        
        # Fill in missing days with 0
        current_date = start_date
        daily_data = []
        
        while current_date <= end_date:
            daily_data.append({
                "date": str(current_date),
                "count": daily_counts.get(current_date, 0)
            })
            current_date += timedelta(days=1)
        
        return daily_data
