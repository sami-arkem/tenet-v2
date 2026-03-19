from src.memory.trend_intelligence import write_all_entity_trend_summaries

written = write_all_entity_trend_summaries()
print("trend_summary_count:", len(written))
for path in written[:20]:
    print("trend_summary:", path)
