#!/usr/bin/env python3
"""Generate intelligent storylines using Data Golf API data.

This module combines:
- Data Golf skill ratings (strokes-gained components)
- Course-specific fit adjustments
- Historical performance patterns
- Course characteristics database

To generate insights like:
- "JJ Spaun ranks 3rd in SG: Putting on Bermuda greens this season"
- "Scheffler's course history adjustment (+0.16) is highest in the field"
- "Young's driving distance advantage is amplified at this bombers' course"
"""
import os
import sys
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Script lives in scripts/legacy/; project root is 2 levels up
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from mcp_server.tools.datagolf import DataGolfClient


@dataclass
class PlayerInsight:
    """A single insight about a player."""
    player_name: str
    dg_id: int
    category: str  # 'skill', 'course_fit', 'form', 'historical'
    insight: str
    metric_value: Optional[float] = None
    rank_in_field: Optional[int] = None
    confidence: str = "high"  # 'high', 'medium', 'low'


class IntelligentStorylineGenerator:
    """Generates intelligent storylines from Data Golf and course data."""

    def __init__(self, api_key: Optional[str] = None):
        self.dg_client = DataGolfClient(api_key=api_key)
        self.course_db = self._load_course_database()

    def _load_course_database(self) -> dict:
        """Load course characteristics database."""
        course_file = _PROJECT_ROOT / "data" / "course_characteristics.json"
        if course_file.exists():
            with open(course_file) as f:
                return json.load(f)
        return {"courses": {}, "grass_types": {}, "skill_correlations": {}}

    def get_course_info(self, event_name: str) -> Optional[dict]:
        """Find course info by tournament name."""
        event_lower = event_name.lower()
        for course_id, info in self.course_db.get("courses", {}).items():
            if event_lower in info.get("tournament", "").lower():
                return info
            if event_lower in info.get("name", "").lower():
                return info
        return None

    def generate_storylines(self, tour: str = "pga") -> dict:
        """Generate intelligent storylines for the current event.

        Returns:
            Dict with event info and list of player storylines
        """
        # Fetch all the data we need
        print("Fetching field updates...")
        field = self.dg_client.get_field_updates(tour=tour)

        print("Fetching pre-tournament predictions...")
        predictions = self.dg_client.get_pre_tournament_predictions(tour=tour)

        print("Fetching skill ratings...")
        skill_ratings = self.dg_client.get_player_skill_ratings()

        print("Fetching course-specific decompositions...")
        decompositions = self.dg_client.get_player_skill_decompositions(tour=tour)

        event_name = predictions.get("event_name", "Unknown Event")
        course_name = decompositions.get("course_name", "Unknown Course")

        # Get course characteristics
        course_info = self.get_course_info(event_name)

        # Build lookup maps
        field_ids = {p.dg_id for p in field}
        skill_map = {s.dg_id: s for s in skill_ratings}
        decomp_map = {p["dg_id"]: p for p in decompositions.get("players", [])}
        pred_map = {p.dg_id: p for p in predictions.get("predictions", [])}

        # Generate insights for each player
        player_storylines = []

        for player in field:
            insights = []

            # Get player's data
            skills = skill_map.get(player.dg_id)
            decomp = decomp_map.get(player.dg_id, {})
            pred = pred_map.get(player.dg_id)

            # 1. SKILL-BASED INSIGHTS
            if skills:
                skill_insights = self._generate_skill_insights(
                    player, skills, skill_ratings, field_ids, course_info
                )
                insights.extend(skill_insights)

            # 2. COURSE FIT INSIGHTS
            if decomp:
                fit_insights = self._generate_course_fit_insights(
                    player, decomp, decompositions.get("players", []), course_info
                )
                insights.extend(fit_insights)

            # 3. PREDICTION-BASED INSIGHTS
            if pred:
                pred_insights = self._generate_prediction_insights(
                    player, pred, predictions.get("predictions", [])
                )
                insights.extend(pred_insights)

            # Combine insights into a storyline
            if insights:
                storyline = self._combine_insights_to_storyline(
                    player.player_name, insights, course_info
                )
                player_storylines.append({
                    "player_name": player.player_name,
                    "dg_id": player.dg_id,
                    "storyline": storyline,
                    "insights": [
                        {"category": i.category, "text": i.insight, "confidence": i.confidence}
                        for i in insights
                    ],
                    "key_stats": self._extract_key_stats(skills, decomp, pred)
                })

        return {
            "event_name": event_name,
            "course_name": course_name,
            "course_info": course_info,
            "player_count": len(player_storylines),
            "storylines": player_storylines
        }

    def _generate_skill_insights(
        self, player, skills, all_skills, field_ids, course_info
    ) -> list[PlayerInsight]:
        """Generate insights based on player's strokes-gained skills."""
        insights = []

        # Filter to only in-field players
        field_skills = [s for s in all_skills if s.dg_id in field_ids]

        # Rank this player in each SG category among field
        sg_categories = [
            ("sg_total", "overall"),
            ("sg_ott", "off the tee"),
            ("sg_app", "on approach"),
            ("sg_arg", "around the green"),
            ("sg_putt", "with the putter"),
        ]

        for attr, desc in sg_categories:
            value = getattr(skills, attr, None)
            if value is None:
                continue

            # Calculate rank in field
            sorted_field = sorted(
                field_skills,
                key=lambda x: getattr(x, attr) or -999,
                reverse=True
            )
            rank = next(
                (i + 1 for i, s in enumerate(sorted_field) if s.dg_id == skills.dg_id),
                None
            )

            if rank and rank <= 5:
                confidence = "high" if rank <= 3 else "medium"
                insight = f"Ranks #{rank} in SG: {desc.title()} among the field ({value:+.2f})"
                insights.append(PlayerInsight(
                    player_name=player.player_name,
                    dg_id=player.dg_id,
                    category="skill",
                    insight=insight,
                    metric_value=value,
                    rank_in_field=rank,
                    confidence=confidence
                ))

            # Check if skill matches course demands
            if course_info:
                key_skills = course_info.get("key_skills", {}).get("primary", [])
                skill_match = {
                    "sg_ott": ["driving_distance", "sg_ott"],
                    "sg_app": ["sg_approach", "iron_play", "ball_striking"],
                    "sg_arg": ["scrambling"],
                    "sg_putt": ["putting_bermuda", "poa_putting", "putting_fast_greens"],
                }
                matches = skill_match.get(attr, [])
                if any(m in key_skills for m in matches) and rank and rank <= 10:
                    course_skill_name = next((m for m in matches if m in key_skills), desc)
                    insight = f"Elite {desc} (#{rank}) aligns with course's premium on {course_skill_name.replace('_', ' ')}"
                    insights.append(PlayerInsight(
                        player_name=player.player_name,
                        dg_id=player.dg_id,
                        category="course_fit",
                        insight=insight,
                        rank_in_field=rank,
                        confidence="high"
                    ))

        # Driving distance for bombers courses
        if course_info:
            bombers_adv = course_info.get("scoring_profile", {}).get("bombers_advantage", "")
            if bombers_adv in ["high", "very_high"] and skills.driving_dist:
                sorted_by_dist = sorted(
                    field_skills,
                    key=lambda x: x.driving_dist or -999,
                    reverse=True
                )
                dist_rank = next(
                    (i + 1 for i, s in enumerate(sorted_by_dist) if s.dg_id == skills.dg_id),
                    None
                )
                if dist_rank and dist_rank <= 10:
                    insight = f"Driving distance (#{dist_rank} in field) is a weapon at this bombers' course"
                    insights.append(PlayerInsight(
                        player_name=player.player_name,
                        dg_id=player.dg_id,
                        category="course_fit",
                        insight=insight,
                        rank_in_field=dist_rank,
                        confidence="high"
                    ))

        return insights

    def _generate_course_fit_insights(
        self, player, decomp: dict, all_decomp: list, course_info: Optional[dict]
    ) -> list[PlayerInsight]:
        """Generate insights from course-fit decomposition data."""
        insights = []

        # Key adjustments to analyze
        adjustments = [
            ("course_history_adjustment", "course history"),
            ("total_fit_adjustment", "overall course fit"),
            ("driving_distance_adjustment", "driving distance advantage"),
            ("driving_accuracy_adjustment", "accuracy premium"),
        ]

        for adj_key, desc in adjustments:
            value = decomp.get(adj_key)
            if value is None:
                continue

            # Rank in field
            sorted_decomp = sorted(
                all_decomp,
                key=lambda x: x.get(adj_key, -999),
                reverse=True
            )
            rank = next(
                (i + 1 for i, d in enumerate(sorted_decomp) if d.get("dg_id") == player.dg_id),
                None
            )

            # Positive adjustments help
            if value > 0.05 and rank and rank <= 10:
                insight = f"Gains {value:+.3f} strokes from {desc} (#{rank} in field)"
                insights.append(PlayerInsight(
                    player_name=player.player_name,
                    dg_id=player.dg_id,
                    category="course_fit",
                    insight=insight,
                    metric_value=value,
                    rank_in_field=rank,
                    confidence="high"
                ))

            # Significant course history
            if adj_key == "course_history_adjustment":
                history_adj = decomp.get("course_history_adjustment", 0)
                if history_adj and history_adj > 0.1 and rank and rank <= 5:
                    insight = f"Strong course history: gains {history_adj:+.2f} strokes vs baseline"
                    insights.append(PlayerInsight(
                        player_name=player.player_name,
                        dg_id=player.dg_id,
                        category="historical",
                        insight=insight,
                        metric_value=history_adj,
                        rank_in_field=rank,
                        confidence="high"
                    ))

        return insights

    def _generate_prediction_insights(
        self, player, pred, all_preds: list
    ) -> list[PlayerInsight]:
        """Generate insights from prediction data."""
        insights = []

        # Win probability ranking
        if pred.win_prob:
            sorted_by_win = sorted(
                all_preds,
                key=lambda x: x.win_prob or 0,
                reverse=True
            )
            win_rank = next(
                (i + 1 for i, p in enumerate(sorted_by_win) if p.dg_id == pred.dg_id),
                None
            )
            if win_rank and win_rank <= 10:
                win_pct = pred.win_prob * 100
                insight = f"Data Golf model: #{win_rank} win probability ({win_pct:.1f}%)"
                insights.append(PlayerInsight(
                    player_name=player.player_name,
                    dg_id=player.dg_id,
                    category="prediction",
                    insight=insight,
                    metric_value=pred.win_prob,
                    rank_in_field=win_rank,
                    confidence="high"
                ))

        # Top 10 value (high make cut but moderate win prob = consistent)
        if pred.make_cut_prob and pred.top_10_prob:
            make_cut_pct = pred.make_cut_prob * 100
            top10_pct = pred.top_10_prob * 100
            if make_cut_pct > 90 and top10_pct > 30:
                insight = f"High-floor play: {make_cut_pct:.0f}% make cut, {top10_pct:.0f}% top-10"
                insights.append(PlayerInsight(
                    player_name=player.player_name,
                    dg_id=player.dg_id,
                    category="prediction",
                    insight=insight,
                    confidence="medium"
                ))

        return insights

    def _extract_key_stats(self, skills, decomp: dict, pred) -> dict:
        """Extract key stats for display."""
        stats = {}

        if skills:
            stats["sg_total"] = skills.sg_total
            stats["sg_ott"] = skills.sg_ott
            stats["sg_app"] = skills.sg_app
            stats["sg_arg"] = skills.sg_arg
            stats["sg_putt"] = skills.sg_putt
            stats["driving_dist"] = skills.driving_dist
            stats["driving_acc"] = skills.driving_acc

        if decomp:
            stats["course_fit_adj"] = decomp.get("total_fit_adjustment")
            stats["course_history_adj"] = decomp.get("course_history_adjustment")
            stats["final_pred"] = decomp.get("final_pred")
            stats["baseline_pred"] = decomp.get("baseline_pred")

        if pred:
            stats["win_prob"] = pred.win_prob
            stats["top_5_prob"] = pred.top_5_prob
            stats["top_10_prob"] = pred.top_10_prob
            stats["make_cut_prob"] = pred.make_cut_prob

        return stats

    def _combine_insights_to_storyline(
        self, player_name: str, insights: list[PlayerInsight], course_info: Optional[dict]
    ) -> str:
        """Combine multiple insights into a cohesive storyline."""

        # Prioritize insights by confidence and category
        high_confidence = [i for i in insights if i.confidence == "high"]
        medium_confidence = [i for i in insights if i.confidence == "medium"]

        # Build storyline from best insights
        storyline_parts = []

        # Lead with skill or course fit insight
        skill_insights = [i for i in high_confidence if i.category in ["skill", "course_fit"]]
        if skill_insights:
            best = skill_insights[0]
            storyline_parts.append(best.insight)

        # Add historical insight if available
        historical = [i for i in high_confidence if i.category == "historical"]
        if historical:
            storyline_parts.append(historical[0].insight)

        # Add prediction insight
        pred_insights = [i for i in high_confidence if i.category == "prediction"]
        if pred_insights:
            storyline_parts.append(pred_insights[0].insight)

        # If no high confidence, use medium
        if not storyline_parts and medium_confidence:
            storyline_parts.append(medium_confidence[0].insight)

        # Add course context if available
        if course_info and storyline_parts:
            course_notes = course_info.get("key_skills", {}).get("notes", "")
            if len(storyline_parts) < 3 and course_notes:
                # Only add if we don't have many insights
                pass  # Could add course-specific context here

        return " ".join(storyline_parts) if storyline_parts else "Solid player in the field."

    def close(self):
        """Clean up resources."""
        self.dg_client.close()


def main():
    """Generate and display intelligent storylines."""
    print("=" * 70)
    print("INTELLIGENT STORYLINE GENERATOR")
    print("=" * 70)

    generator = IntelligentStorylineGenerator()

    try:
        result = generator.generate_storylines(tour="pga")

        print(f"\nEvent: {result['event_name']}")
        print(f"Course: {result['course_name']}")
        print(f"Field Size: {result['player_count']}")

        if result.get("course_info"):
            ci = result["course_info"]
            print(f"\nCourse Profile:")
            print(f"  Par: {ci.get('characteristics', {}).get('par')}")
            print(f"  Yardage: {ci.get('characteristics', {}).get('yardage')}")
            print(f"  Grass: {ci.get('characteristics', {}).get('grass_type')}")
            print(f"  Bombers Advantage: {ci.get('scoring_profile', {}).get('bombers_advantage')}")
            print(f"  Key Skills: {', '.join(ci.get('key_skills', {}).get('primary', []))}")

        print("\n" + "=" * 70)
        print("SAMPLE STORYLINES (Top 15 players with best insights)")
        print("=" * 70)

        # Sort by number of high-confidence insights
        sorted_storylines = sorted(
            result["storylines"],
            key=lambda x: len([i for i in x["insights"] if i["confidence"] == "high"]),
            reverse=True
        )

        for i, player in enumerate(sorted_storylines[:15], 1):
            print(f"\n{i}. {player['player_name']}")
            print(f"   {player['storyline']}")

            # Show key stats
            stats = player.get("key_stats", {})
            if stats.get("sg_total"):
                print(f"   SG Total: {stats['sg_total']:+.2f} | "
                      f"OTT: {stats.get('sg_ott', 0):+.2f} | "
                      f"APP: {stats.get('sg_app', 0):+.2f} | "
                      f"PUTT: {stats.get('sg_putt', 0):+.2f}")
            if stats.get("win_prob"):
                print(f"   Win: {stats['win_prob']*100:.1f}% | "
                      f"Top 10: {stats.get('top_10_prob', 0)*100:.1f}%")

        # Save full output to JSON
        output_file = _PROJECT_ROOT / "data" / "intelligent_storylines.json"
        with open(output_file, "w") as f:
            # Convert dataclass objects to dicts for serialization
            json.dump(result, f, indent=2, default=str)
        print(f"\n\nFull output saved to: {output_file}")

    finally:
        generator.close()


if __name__ == "__main__":
    main()
