#!/usr/bin/env python3

import argparse
import csv
import math

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from sys import exit


@dataclass(frozen=True)
class TopicGrowth:
    topic_id: int
    words: str
    growth_rate: float
    slope_per_year: float
    start_frequency: float
    end_frequency: float
    absolute_change: float
    relative_change: float
    observations: int
    start_timestamp: datetime
    end_timestamp: datetime

def parse_timestamp(value: str) -> datetime:
    '''Parse ISO 8601 timestamp, stripping any leading/trailing whitespace'''
    return datetime.fromisoformat(value.strip())

def parse_start_date(value: str) -> datetime:
    '''Parse start date in YYYY-MM-DD format and return a datetime at the start of that day'''
    return datetime.combine(date.fromisoformat(value), datetime.min.time())

def linear_regression_slope(x_values: list[float], y_values: list[float]) -> float:
    '''Calculate the slope of the best-fit line through time (x_values) and log-transformed frequencies (y_values).'''
    mean_x = sum(x_values) / len(x_values)
    mean_y = sum(y_values) / len(y_values)

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    denominator = sum((x - mean_x) ** 2 for x in x_values)

    if denominator == 0:
        return 0.0

    return numerator / denominator

def collect_available_timestamps(csv_file: str) -> list[datetime]:
    '''Collect all unique timestamps from the CSV file and return them sorted.'''
    timestamps: set[datetime] = set()

    with open(csv_file, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            topic_id = int(row["Topic"])
            if topic_id != -1:
                timestamps.add(parse_timestamp(row["Timestamp"]))

    return sorted(timestamps)

def calculate_topic_growth(csv_file: str, start_date: datetime | None = None,) -> list[TopicGrowth]:
    '''Calculate the growth rate of each topic based on the frequencies over time.'''
    topics: dict[int, list[tuple[datetime, float, str]]] = defaultdict(list)

    with open(csv_file, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"Topic", "Words", "Frequency", "Timestamp"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing required columns: {missing}")

        for row in reader:
            topic_id = int(row["Topic"])
            if topic_id == -1:
                continue

            timestamp = parse_timestamp(row["Timestamp"])
            if start_date is not None:
                if timestamp < start_date:
                    continue
            frequency = float(row["Frequency"])
            words = row["Words"].strip()
            topics[topic_id].append((timestamp, frequency, words))

    topic_growth: list[TopicGrowth] = []

    for topic_id, records in topics.items():
        if len(records) < 2:
            print(f"Skipping topic {topic_id} because it has fewer than 2 observations.")
            continue

        records.sort(key=lambda item: item[0])
        start_timestamp = records[0][0]
        end_timestamp = records[-1][0]
        span_years = (end_timestamp - start_timestamp).total_seconds() / (365.25 * 24 * 60 * 60)

        # Calculate slope of log-transformed frequencies over time
        if span_years == 0:
            slope_per_year = 0.0
        else:
            # Get time in years since the start timestamp for each observation
            x_values = [((timestamp - start_timestamp).total_seconds() / (365.25 * 24 * 60 * 60)) for timestamp, _, _ in records]
            # Get log-transformed frequencies, using log1p to handle zero frequencies gracefully
            y_values = [math.log1p(frequency) for _, frequency, _ in records]
            # Calculate the slope of the best-fit line through the log-transformed frequencies over time
            slope_per_year = linear_regression_slope(x_values, y_values)

        # Get annual growth rate
        growth_rate = math.expm1(slope_per_year)

        # Get absolute and relative change in paper count
        start_frequency = records[0][1]
        end_frequency = records[-1][1]
        absolute_change = end_frequency - start_frequency
        relative_change = (absolute_change / start_frequency) if start_frequency else math.inf

        # Get topic words
        words = records[-1][2]

        topic_growth.append(
            TopicGrowth(
                topic_id=topic_id,
                words=words,
                growth_rate=growth_rate,
                slope_per_year=slope_per_year,
                start_frequency=start_frequency,
                end_frequency=end_frequency,
                absolute_change=absolute_change,
                relative_change=relative_change,
                observations=len(records),
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
        )

    topic_growth.sort(key=lambda item: (item.growth_rate, item.absolute_change), reverse=True)
    return topic_growth

def print_available_timestamps(timestamps: list[datetime]):
    '''Print all available timestamps in the CSV file.'''
    print("Available timestamps in the CSV:")
    for timestamp in timestamps:
        print(f"- {timestamp.isoformat(sep=' ')}")

def setup_parser() -> argparse.Namespace:
    '''Set up CLI parser and parse args.'''
    parser = argparse.ArgumentParser(description="Rank topics by annualized growth rate from a BERTopic topics_over_time CSV file.")
    parser.add_argument("csv_file", help="Path to the BERTopic topics_over_time CSV file")
    parser.add_argument("-n", "--top-n", type=int, default=10, help="Number of top growing topics to display")
    parser.add_argument(
        "--start-date",
        type=parse_start_date,
        help="Only consider time bins on or after this YYYY-MM-DD date",
    )
    args = parser.parse_args()

    if args.start_date:
        available_timestamps = collect_available_timestamps(args.csv_file)
        if not available_timestamps:
            print("The CSV does not contain any timestamps after applying the selected filters.")
            exit(1)

        if args.start_date > available_timestamps[-1]:
            print(
                f"No data is available on or after {args.start_date.date().isoformat()}. "
                f"The latest timestamp in the CSV is {available_timestamps[-1].isoformat(sep=' ')}."
            )
            print_available_timestamps(available_timestamps)
            exit(1)

    return args

def format_rate(value: float) -> str:
    '''Format the growth rate as a percentage with two decimal places, or "inf" if it's infinite.'''
    if math.isinf(value):
        return "inf"
    return f"{value:.2%}"

def format_change(value: float) -> str:
    '''Format the paper count change as a whole number.'''
    return f"{value:.0f}"

def print_topic_growth(topic_growth: list[TopicGrowth], top_n: int):
    '''Print the top N growing topics in a formatted table.'''
    print("Topic ID | Growth rate | Paper count change | Final representation words")
    print("-" * 110)

    for rank, item in enumerate(topic_growth[:top_n], start=1):
        print(
            f"{item.topic_id:>8} | "
            f"{format_rate(item.growth_rate):>11} | "
            f"{format_change(item.absolute_change):>18} | "
            f"{item.words}"
        )

def main():
    args = setup_parser()

    topic_growth = calculate_topic_growth(args.csv_file, start_date=args.start_date)

    if not topic_growth:
        print("No topics met the minimum observation threshold after applying the selected filters.")
        if args.start_date is not None:
            available_timestamps = collect_available_timestamps(args.csv_file)
            print_available_timestamps(available_timestamps)
        exit(1)

    print_topic_growth(topic_growth, args.top_n)


if __name__ == "__main__":
    main()
