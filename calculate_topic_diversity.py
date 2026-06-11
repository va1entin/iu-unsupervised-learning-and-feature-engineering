#!/usr/bin/env python3

import csv
import argparse

def setup_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calculate topic diversity from a CSV file of topic ids and words like 'topic_id1;word1,word2,...'")
    parser.add_argument("csv_file", help="Path to the CSV file")
    parser.add_argument("-k", type=int, default=10, help="Number of top words per topic")
    parser.add_argument("-d", action="store_true", help="Show debug information")
    args = parser.parse_args()

    return args

def calculate_topic_diversity(csv_file, k=10, debug=False) -> float:
    unique_words = set()
    total_topics = 0

    with open(csv_file, 'r') as f:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            if not row:
                continue
            topic_id = row[0]
            words = [w.strip() for w in row[1].split(',') if w]
            if debug:
                print(f"  Adding words for topic {topic_id}: {words}")
            unique_words.update(words)
            total_topics += 1

    T = total_topics
    D = len(unique_words)
    diversity = D / (T * k)

    if debug:
        print(f"Total unique words: {D}")
        print(f"Total topics: {T}")
        print(f"Top-k words per topic: {k}")
        print(f"Unique words: {unique_words}")
        print()

    return diversity

def main():
    args = setup_parser()

    diversity = calculate_topic_diversity(args.csv_file, args.k, args.d)
    print(f"Topic Diversity for {args.csv_file}:\n{diversity}")

if __name__ == "__main__":
    main()