#!/usr/bin/env python3
"""Demo data seeding script for jcselect."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import bcrypt
from faker import Faker
from jcselect.models import AuditLog, Party, Pen, TallyLine, TallySession, User, Voter
from jcselect.utils.db import get_session
from loguru import logger
from sqlmodel import select

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if TYPE_CHECKING:
    from sqlmodel import Session

# Lebanese names for realistic data
LEBANESE_FIRST_NAMES_MALE = [
    "Ahmad",
    "Ali",
    "Hassan",
    "Hussein",
    "Mohammad",
    "Omar",
    "Khalil",
    "Samir",
    "Maroun",
    "Antoine",
    "Georges",
    "Pierre",
    "Jean",
    "Michel",
    "Elie",
    "Fadi",
    "Rami",
    "Karim",
    "Nader",
    "Walid",
    "Ziad",
    "Bassam",
    "Ghassan",
    "Imad",
    "Jihad",
    "Mazen",
    "Rabih",
    "Sami",
    "Tarek",
    "Youssef",
]

LEBANESE_FIRST_NAMES_FEMALE = [
    "Fatima",
    "Aisha",
    "Khadija",
    "Maryam",
    "Zahra",
    "Layla",
    "Nour",
    "Rana",
    "Marie",
    "Rita",
    "Carla",
    "Nadia",
    "Joelle",
    "Rima",
    "Lara",
    "Maya",
    "Dina",
    "Hala",
    "Lina",
    "Mona",
    "Rania",
    "Samar",
    "Tala",
    "Yasmin",
    "Zeina",
    "Ghada",
    "Hanane",
    "Iman",
    "Najwa",
    "Widad",
]

LEBANESE_LAST_NAMES = [
    "Khoury",
    "Haddad",
    "Khalil",
    "Mansour",
    "Nader",
    "Saad",
    "Tannous",
    "Zein",
    "Abou Khalil",
    "El Khoury",
    "Hariri",
    "Gemayel",
    "Frangieh",
    "Chamoun",
    "Salam",
    "Karami",
    "Mikati",
    "Berri",
    "Aoun",
    "Geagea",
    "Jumblatt",
    "Arslan",
    "Talhouk",
    "Fares",
    "Maatouk",
    "Sleiman",
    "Azar",
    "Bou Saab",
    "Daccache",
    "Frem",
]

LEBANESE_PARTIES = [
    ("Future Movement", "FM"),
    ("Free Patriotic Movement", "FPM"),
    ("Lebanese Forces", "LF"),
    ("Progressive Socialist Party", "PSP"),
    ("Amal Movement", "AMAL"),
    ("Hezbollah", "HZB"),
    ("Kataeb Party", "KTB"),
    ("Marada Movement", "MAR"),
    ("Tashnag Party", "TASH"),
    ("Lebanese Democratic Party", "LDP"),
    ("National Liberal Party", "NLP"),
    ("Solidarity Party", "SOL"),
    ("Independence Movement", "IND"),
    ("Change and Reform", "CR"),
    ("Strong Lebanon", "SL"),
    ("National Bloc", "NB"),
    ("Renewal Movement", "REN"),
    ("Citizens in a State", "CIS"),
    ("Sabaa Party", "SAB"),
    ("Together for Change", "TFC"),
]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_pens(session: Session) -> list[Pen]:
    """Create demo pen data."""
    pens_data = [
        {"town_name": "Beirut", "label": "Pen 101"},
        {"town_name": "Tripoli", "label": "Pen 102"},
        {"town_name": "Sidon", "label": "Pen 103"},
    ]

    pens = []
    for pen_data in pens_data:
        pen = Pen(**pen_data)
        session.add(pen)
        pens.append(pen)

    session.flush()  # Get IDs
    logger.info(f"Created {len(pens)} pens")
    return pens


def create_parties(session: Session) -> list[Party]:
    """Create demo party data."""
    parties = []
    for i, (name, short_code) in enumerate(LEBANESE_PARTIES):
        party = Party(
            name=name, short_code=short_code, display_order=i + 1, is_active=True
        )
        session.add(party)
        parties.append(party)

    session.flush()  # Get IDs
    logger.info(f"Created {len(parties)} parties")
    return parties


def create_users(session: Session) -> list[User]:
    """Create demo user data."""
    users_data = [
        {
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "full_name": "System Administrator",
            "role": "admin",
            "is_active": True,
        },
        {
            "username": "operator1",
            "password_hash": hash_password("operator123"),
            "full_name": "Election Operator",
            "role": "operator",
            "is_active": True,
        },
    ]

    users = []
    for user_data in users_data:
        user = User(**user_data)
        session.add(user)
        users.append(user)

    session.flush()  # Get IDs
    logger.info(f"Created {len(users)} users")
    return users


def create_voters(session: Session, pens: list[Pen]) -> list[Voter]:
    """Create demo voter data."""
    fake = Faker()
    voters = []

    # Distribute 100 voters across 3 pens
    voters_per_pen = [34, 33, 33]  # Total: 100

    for pen_idx, pen in enumerate(pens):
        voter_count = voters_per_pen[pen_idx]

        for voter_num in range(1, voter_count + 1):
            # Randomly choose gender
            gender = fake.random_element(elements=("M", "F"))

            # Choose appropriate name based on gender
            if gender == "M":
                first_name = fake.random_element(elements=LEBANESE_FIRST_NAMES_MALE)
            else:
                first_name = fake.random_element(elements=LEBANESE_FIRST_NAMES_FEMALE)

            last_name = fake.random_element(elements=LEBANESE_LAST_NAMES)
            full_name = f"{first_name} {last_name}"

            # Generate father and mother names
            father_first = fake.random_element(elements=LEBANESE_FIRST_NAMES_MALE)
            father_name = f"{father_first} {last_name}"

            mother_first = fake.random_element(elements=LEBANESE_FIRST_NAMES_FEMALE)
            mother_last = fake.random_element(elements=LEBANESE_LAST_NAMES)
            mother_name = f"{mother_first} {mother_last}"

            voter = Voter(
                pen_id=pen.id,
                voter_number=f"{voter_num:03d}",  # 001, 002, etc.
                full_name=full_name,
                father_name=father_name,
                mother_name=mother_name,
                birth_year=fake.random_int(min=1950, max=2005),
                gender=gender,
                has_voted=fake.boolean(chance_of_getting_true=20),  # 20% already voted
                voted_at=None,  # Will be set when marking as voted
                voted_by_operator_id=None,
            )

            session.add(voter)
            voters.append(voter)

    session.flush()  # Get IDs
    logger.info(f"Created {len(voters)} voters across {len(pens)} pens")
    return voters


def print_summary(session: Session) -> None:
    """Print summary of seeded data."""
    counts = {}

    # Count each entity type
    for model_class in [Pen, Party, User, Voter, TallySession, TallyLine, AuditLog]:
        count = len(session.exec(select(model_class)).all())
        counts[model_class.__name__] = count

    print("\n" + "=" * 50)
    print("DATABASE SEEDING SUMMARY")
    print("=" * 50)

    for entity_name, count in counts.items():
        print(f"{entity_name:15}: {count:4d} records")

    print("=" * 50)
    print("✅ Demo data seeding completed successfully!")
    print("\nTo view the data:")
    print("  sqlite3 ~/.jcselect/local.db '.tables'")
    print("  sqlite3 ~/.jcselect/local.db 'SELECT COUNT(*) FROM voters;'")
    print("=" * 50)


def main() -> None:
    """Main seeding function."""
    logger.info("Starting demo data seeding...")

    try:
        with get_session() as session:
            # Check if data already exists (idempotency)
            existing_pens = session.exec(select(Pen)).all()
            if existing_pens:
                logger.info(
                    f"Found {len(existing_pens)} existing pens. Skipping seeding to maintain idempotency."
                )
                print("⚠️  Database already contains data. Skipping seeding.")
                print("   To re-seed, delete the database file and run again:")
                print("   rm ~/.jcselect/local.db")
                return

            # Create all demo data
            logger.info("Creating demo data...")

            create_pens(session)
            create_parties(session)
            create_users(session)
            create_voters(session, session.exec(select(Pen)).all())

            # Commit all changes
            session.commit()
            logger.info("All demo data committed to database")

            # Print summary
            print_summary(session)

    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
