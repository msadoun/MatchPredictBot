from database import init_db, seed_world_cup_matches


def main() -> None:
    init_db()
    stats = seed_world_cup_matches()
    print(
        f"World Cup 2026 seed complete: "
        f"{stats['added']} added, {stats['skipped']} skipped, "
        f"{stats['closed']} past matches closed."
    )


if __name__ == "__main__":
    main()
