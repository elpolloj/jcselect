#!/usr/bin/env python3
"""Performance testing script for voter search functionality."""

import time
from pathlib import Path
from uuid import uuid4

from faker import Faker
from sqlmodel import Session, create_engine, select

from jcselect.models import User, Voter, Pen
from jcselect.controllers.voter_search_controller import VoterSearchController
from jcselect.utils.db import get_session


def seed_test_data(num_voters: int = 1000) -> None:
    """Seed the database with fake voter data for performance testing."""
    fake = Faker(['ar_SA', 'en_US'])  # Arabic and English faker
    
    print(f"Seeding {num_voters} fake voters...")
    
    with get_session() as session:
        # Create a test pen if it doesn't exist
        test_pen = session.exec(select(Pen).where(Pen.label == "Test Pen")).first()
        if not test_pen:
            test_pen = Pen(
                id=uuid4(),
                label="Test Pen",
                description="Test pen for performance testing",
                max_capacity=num_voters
            )
            session.add(test_pen)
            session.commit()
            session.refresh(test_pen)
        
        # Check if test data already exists
        existing_count = session.exec(select(Voter).where(Voter.pen_id == test_pen.id)).all()
        if len(existing_count) >= num_voters:
            print(f"Test data already exists ({len(existing_count)} voters)")
            return
        
        # Clear existing test data
        for voter in existing_count:
            session.delete(voter)
        
        voters = []
        for i in range(num_voters):
            # Generate Arabic and English names
            arabic_first = fake.first_name()
            arabic_last = fake.last_name() 
            full_name = f"{arabic_first} {arabic_last}"
            
            father_name = fake.first_name()
            mother_name = fake.first_name()
            
            voter = Voter(
                id=uuid4(),
                voter_number=f"TEST{i+1:06d}",  # TEST000001, TEST000002, etc.
                full_name=full_name,
                father_name=father_name,
                mother_name=mother_name,
                pen_id=test_pen.id,
                has_voted=fake.boolean(chance_of_getting_true=30),  # 30% voted
                voted_at=fake.date_time_this_year() if fake.boolean(chance_of_getting_true=30) else None
            )
            voters.append(voter)
            
            if len(voters) >= 100:  # Batch insert for performance
                session.add_all(voters)
                session.commit()
                voters = []
                print(f"  Inserted {i+1} voters...")
        
        if voters:  # Insert remaining voters
            session.add_all(voters)
            session.commit()
        
        print(f"✅ Successfully seeded {num_voters} test voters")


def test_search_performance() -> None:
    """Test search performance with different query types."""
    print("\n" + "="*60)
    print("SEARCH PERFORMANCE TESTING")
    print("="*60)
    
    controller = VoterSearchController()
    
    test_cases = [
        ("Exact number match", "TEST000001"),
        ("Partial number match", "TEST00001"),
        ("Number prefix", "TEST"),
        ("Common Arabic name", "محمد"),  # Mohammed
        ("Name fragment", "أحمد"),       # Ahmed
        ("Father name search", "علي"),   # Ali
    ]
    
    results = []
    
    for test_name, query in test_cases:
        print(f"\n🔍 Testing: {test_name}")
        print(f"   Query: '{query}'")
        
        # Warm up the query
        controller._set_search_query(query)
        controller._perform_search()
        
        # Time multiple runs
        times = []
        for run in range(5):
            start_time = time.perf_counter()
            controller._set_search_query(query)
            controller._perform_search()
            end_time = time.perf_counter()
            
            duration_ms = (end_time - start_time) * 1000
            times.append(duration_ms)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        result_count = len(controller._search_results)
        
        results.append((test_name, query, avg_time, min_time, max_time, result_count))
        
        status = "✅" if avg_time < 10 else "⚠️" if avg_time < 50 else "❌"
        print(f"   {status} Average: {avg_time:.2f}ms (min: {min_time:.2f}ms, max: {max_time:.2f}ms)")
        print(f"   📊 Results: {result_count} voters found")
    
    # Performance summary
    print(f"\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    print(f"{'Test Case':<25} {'Query':<15} {'Avg (ms)':<10} {'Results':<10} {'Status'}")
    print("-" * 70)
    
    for test_name, query, avg_time, min_time, max_time, result_count in results:
        status = "EXCELLENT" if avg_time < 10 else "GOOD" if avg_time < 50 else "NEEDS WORK"
        print(f"{test_name:<25} {query:<15} {avg_time:>7.2f} {result_count:>9} {status}")
    
    overall_avg = sum(r[2] for r in results) / len(results)
    print(f"\n🎯 Overall average search time: {overall_avg:.2f}ms")
    
    if overall_avg < 10:
        print("🚀 EXCELLENT: All searches under 10ms target!")
    elif overall_avg < 50:
        print("✅ GOOD: Average search time acceptable")
    else:
        print("⚠️  ATTENTION: Search performance may need optimization")


def cleanup_test_data() -> None:
    """Remove test data from the database."""
    print("\n🧹 Cleaning up test data...")
    
    with get_session() as session:
        # Delete test voters
        test_voters = session.exec(
            select(Voter).where(Voter.voter_number.startswith("TEST"))
        ).all()
        
        for voter in test_voters:
            session.delete(voter)
        
        # Delete test pen
        test_pen = session.exec(select(Pen).where(Pen.label == "Test Pen")).first()
        if test_pen:
            session.delete(test_pen)
        
        session.commit()
        print(f"✅ Removed {len(test_voters)} test voters and test pen")


def main():
    """Main performance testing function."""
    print("🔧 VOTER SEARCH PERFORMANCE TESTING")
    print("="*40)
    
    try:
        # Seed test data
        seed_test_data(1000)
        
        # Run performance tests
        test_search_performance()
        
        # Ask user if they want to keep test data
        print(f"\n{'='*60}")
        response = input("Keep test data for further testing? (y/N): ").lower().strip()
        
        if response != 'y':
            cleanup_test_data()
        else:
            print("📝 Test data preserved for future testing")
            
    except Exception as e:
        print(f"❌ Error during performance testing: {e}")
        raise
    
    print("\n✅ Performance testing completed!")


if __name__ == "__main__":
    main() 