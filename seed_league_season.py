from database import init_db, reset_to_league_season


def main() -> None:
    init_db()
    result = reset_to_league_season()
    print(
        "League season reset complete: "
        f"{result['seeded']} matches seeded, "
        f"{result['predictions_cleared']} predictions cleared."
    )


if __name__ == "__main__":
    main()
