"""
seed_data.py
Creates 12 fake ShopX microservices and their dependencies.
Run this once to populate the database with realistic test data.
"""

from models import Service, Dependency
from database import init_db, save_service, save_dependency


def seed():
    # Step 1: initialize database tables
    init_db()

    # ──────────────────────────────────────────────
    # 12 fake ShopX microservices
    # ──────────────────────────────────────────────
    services = [
        Service(
            id="gateway-service",
            name="API Gateway",
            team="Platform",
            criticality="high",
            failure_rate=0.05
        ),
        Service(
            id="auth-service",
            name="Authentication Service",
            team="Security",
            criticality="high",
            failure_rate=0.08
        ),
        Service(
            id="user-service",
            name="User Profile Service",
            team="Core",
            criticality="medium",
            failure_rate=0.06
        ),
        Service(
            id="product-service",
            name="Product Catalog Service",
            team="Catalog",
            criticality="high",
            failure_rate=0.04
        ),
        Service(
            id="inventory-service",
            name="Inventory Service",
            team="Catalog",
            criticality="high",
            failure_rate=0.10
        ),
        Service(
            id="cart-service",
            name="Shopping Cart Service",
            team="Commerce",
            criticality="medium",
            failure_rate=0.07
        ),
        Service(
            id="order-service",
            name="Order Management Service",
            team="Commerce",
            criticality="high",
            failure_rate=0.09
        ),
        Service(
            id="payment-service",
            name="Payment Processing Service",
            team="Finance",
            criticality="high",
            failure_rate=0.03
        ),
        Service(
            id="notification-service",
            name="Notification Service",
            team="Comms",
            criticality="low",
            failure_rate=0.12
        ),
        Service(
            id="search-service",
            name="Search Service",
            team="Discovery",
            criticality="medium",
            failure_rate=0.06
        ),
        Service(
            id="recommendation-service",
            name="Recommendation Engine",
            team="Discovery",
            criticality="low",
            failure_rate=0.08
        ),
        Service(
            id="database-service",
            name="Central Database",
            team="Infrastructure",
            criticality="high",
            failure_rate=0.02
        ),
    ]

    # ──────────────────────────────────────────────
    # Dependencies — who depends on who
    # source depends on target
    # if target fails → source is impacted
    # ──────────────────────────────────────────────
    dependencies = [
        Dependency(
            source_id="gateway-service",
            target_id="auth-service",
            weight=9.0,
            description="Gateway validates every request via Auth"
        ),
        Dependency(
            source_id="auth-service",
            target_id="database-service",
            weight=10.0,
            description="Auth reads/writes user credentials from DB"
        ),
        Dependency(
            source_id="user-service",
            target_id="database-service",
            weight=9.0,
            description="User profiles stored in central DB"
        ),
        Dependency(
            source_id="product-service",
            target_id="database-service",
            weight=8.0,
            description="Product catalog stored in DB"
        ),
        Dependency(
            source_id="inventory-service",
            target_id="database-service",
            weight=8.0,
            description="Stock levels stored in DB"
        ),
        Dependency(
            source_id="cart-service",
            target_id="product-service",
            weight=7.0,
            description="Cart fetches product details"
        ),
        Dependency(
            source_id="cart-service",
            target_id="inventory-service",
            weight=8.0,
            description="Cart checks stock before adding items"
        ),
        Dependency(
            source_id="order-service",
            target_id="payment-service",
            weight=10.0,
            description="Orders cannot complete without payment"
        ),
        Dependency(
            source_id="order-service",
            target_id="inventory-service",
            weight=9.0,
            description="Orders reduce inventory on confirmation"
        ),
        Dependency(
            source_id="order-service",
            target_id="notification-service",
            weight=4.0,
            description="Orders trigger confirmation emails/SMS"
        ),
        Dependency(
            source_id="payment-service",
            target_id="database-service",
            weight=10.0,
            description="Payment records stored in DB"
        ),
        Dependency(
            source_id="search-service",
            target_id="product-service",
            weight=7.0,
            description="Search indexes product catalog"
        ),
        Dependency(
            source_id="recommendation-service",
            target_id="user-service",
            weight=6.0,
            description="Recommendations based on user history"
        ),
        Dependency(
            source_id="recommendation-service",
            target_id="product-service",
            weight=6.0,
            description="Recommendations pull from product catalog"
        ),
    ]

    # ──────────────────────────────────────────────
    # Save everything to database
    # ──────────────────────────────────────────────
    print("Seeding services...")
    for service in services:
        save_service(service)
        print(f"  ✓ {service.id}")

    print("\nSeeding dependencies...")
    for dep in dependencies:
        save_dependency(dep)
        print(f"  ✓ {dep.source_id} → {dep.target_id}")

    print(f"\nDone! {len(services)} services and {len(dependencies)} dependencies seeded.")


if __name__ == "__main__":
    seed()
