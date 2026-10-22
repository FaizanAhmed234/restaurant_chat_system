import streamlit as st
import sqlite3
from datetime import date, time, datetime
from pathlib import Path

# ==========================================
# RESTAURANT AI ASSISTANT
# Initial version: menu, ordering, reservations
# ==========================================

st.set_page_config(
    page_title="Restaurant Assistant",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).parent / "restaurant.db"

# ==========================================
# DATABASE
# ==========================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                available INTEGER DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                order_type TEXT NOT NULL,
                items TEXT NOT NULL,
                total REAL NOT NULL,
                status TEXT DEFAULT 'Pending',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                guests INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                status TEXT DEFAULT 'Pending'
            )
        """)

        count = conn.execute(
            "SELECT COUNT(*) FROM menu"
        ).fetchone()[0]

        if count == 0:
            sample_menu = [
                ("Classic Burger", "Burgers", 180),
                ("Cheese Burger", "Burgers", 220),
                ("Margherita Pizza", "Pizza", 250),
                ("Farmhouse Pizza", "Pizza", 320),
                ("White Sauce Pasta", "Pasta", 230),
                ("French Fries", "Sides", 100),
                ("Cold Coffee", "Drinks", 120),
                ("Chocolate Brownie", "Desserts", 140),
            ]

            conn.executemany("""
                INSERT INTO menu (name, category, price)
                VALUES (?, ?, ?)
            """, sample_menu)


initialize_database()

# ==========================================
# HELPERS
# ==========================================

def fetch_menu(available_only=True):
    with get_connection() as conn:
        query = "SELECT * FROM menu"

        if available_only:
            query += " WHERE available = 1"

        query += " ORDER BY category, name"

        return conn.execute(query).fetchall()


def money(amount):
    return f"₹{amount:,.2f}"


def submit_order(customer, order_type, cart):
    items = []

    for item_id, quantity in cart.items():
        if quantity <= 0:
            continue

        with get_connection() as conn:
            row = conn.execute("""
                SELECT name, price
                FROM menu
                WHERE id = ? AND available = 1
            """, (item_id,)).fetchone()

        if row:
            items.append({
                "name": row[0],
                "quantity": quantity,
                "price": row[1],
            })

    if not items:
        return False, "Your cart is empty or contains unavailable items."

    total = sum(
        item["price"] * item["quantity"]
        for item in items
    )

    order_description = "; ".join(
        f"{item['name']} x {item['quantity']}"
        for item in items
    )

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO orders (
                customer, order_type, items, total, created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            customer.strip(),
            order_type,
            order_description,
            total,
            datetime.now().isoformat(timespec="seconds"),
        ))

    return True, f"Order placed successfully! Total: {money(total)}"


def create_reservation(customer, guests, booking_date, booking_time):
    if booking_date < date.today():
        return False, "Please select today or a future date."

    # Initial demo: prevent duplicate bookings at the same time.
    # Real restaurant table allocation will be added later.
    with get_connection() as conn:
        existing = conn.execute("""
            SELECT COUNT(*)
            FROM reservations
            WHERE booking_date = ?
              AND booking_time = ?
              AND status != 'Cancelled'
        """, (
            booking_date.isoformat(),
            booking_time.strftime("%H:%M"),
        )).fetchone()[0]

        if existing >= 5:
            return False, "That time slot is full in our demo system."

        conn.execute("""
            INSERT INTO reservations (
                customer, guests, booking_date, booking_time
            )
            VALUES (?, ?, ?, ?)
        """, (
            customer.strip(),
            guests,
            booking_date.isoformat(),
            booking_time.strftime("%H:%M"),
        ))

    return True, "Reservation request saved successfully!"


# ==========================================
# STYLING
# ==========================================

st.markdown("""
<style>
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        padding: 1.5rem 0;
    }

    .muted {
        color: #777777;
    }

    div[data-testid="stMetric"] {
        padding: 1rem;
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================

st.sidebar.title("🍽️ Restaurant Assistant")
st.sidebar.caption("Ordering & Reservations")

page = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "Order Food",
        "Book a Table",
        "Restaurant Dashboard",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Portfolio project · Demo version")

# ==========================================
# HOME
# ==========================================

if page == "Home":
    st.title("Your restaurant, simplified.")
    st.write(
        "A simple digital experience for food ordering "
        "and table reservations."
    )

    st.info(
        "Welcome! Browse the menu, place an order, "
        "or reserve a table."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("🍕 Food ordering")
        st.write("Browse dishes, choose quantities, and calculate totals.")

    with col2:
        st.subheader("📅 Reservations")
        st.write("Submit a request for your preferred date and time.")

    with col3:
        st.subheader("📊 Management")
        st.write("Review orders and reservation requests.")

    st.divider()
    st.subheader("Popular dishes")

    menu = fetch_menu()[:4]

    if menu:
        cols = st.columns(4)

        for col, item in zip(cols, menu):
            with col:
                st.markdown(f"**{item[1]}**")
                st.caption(item[2])
                st.write(money(item[3]))

# ==========================================
# ORDER FOOD
# ==========================================

elif page == "Order Food":
    st.title("Order food")
    st.caption("Choose your dishes and review your cart.")

    customer = st.text_input("Your name")

    order_type = st.selectbox(
        "Order type",
        ["Dine-in", "Takeaway", "Delivery"],
    )

    if order_type == "Dine-in":
        st.caption("For a table reservation, use Book a Table.")

    if order_type == "Delivery":
        st.info(
            "Demo mode: delivery address collection "
            "will be added in a later stage."
        )

    menu = fetch_menu()

    if "cart" not in st.session_state:
        st.session_state.cart = {}

    if not menu:
        st.warning("No menu items are currently available.")

    else:
        categories = sorted(set(item[2] for item in menu))

        selected_category = st.selectbox(
            "Food category",
            categories,
        )

        category_items = [
            item for item in menu
            if item[2] == selected_category
        ]

        for item in category_items:
            item_id, name, category, price, available = item

            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**{name}**")
                st.caption(category)

            with col2:
                st.write(money(price))

            with col3:
                current_qty = st.session_state.cart.get(item_id, 0)

                new_qty = st.number_input(
                    "Quantity",
                    min_value=0,
                    max_value=20,
                    value=current_qty,
                    step=1,
                    key=f"qty_{item_id}",
                    label_visibility="collapsed",
                )

                st.session_state.cart[item_id] = new_qty

    st.divider()
    st.subheader("Your cart")

    cart_rows = []
    cart_total = 0.0

    current_menu = {
        item[0]: item
        for item in fetch_menu()
    }

    for item_id, quantity in st.session_state.cart.items():
        item = current_menu.get(item_id)

        if item and quantity > 0:
            subtotal = item[3] * quantity
            cart_total += subtotal

            cart_rows.append({
                "Item": item[1],
                "Quantity": quantity,
                "Subtotal": money(subtotal),
            })

    if cart_rows:
        st.dataframe(
            cart_rows,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader(f"Total: {money(cart_total)}")

        if st.button("Place order", type="primary"):
            if not customer.strip():
                st.error("Please enter your name.")
            else:
                success, message = submit_order(
                    customer,
                    order_type,
                    st.session_state.cart,
                )

                if success:
                    st.success(message)
                    st.session_state.cart = {}
                else:
                    st.error(message)

    else:
        st.caption("Your cart is empty.")

# ==========================================
# BOOK A TABLE
# ==========================================

elif page == "Book a Table":
    st.title("Reserve a table")
    st.write("Submit your preferred date, time, and party size.")

    with st.form("reservation_form"):
        customer = st.text_input("Your name")

        guests = st.number_input(
            "Number of guests",
            min_value=1,
            max_value=20,
            value=2,
        )

        booking_date = st.date_input(
            "Reservation date",
            min_value=date.today(),
            value=date.today(),
        )

        booking_time = st.time_input(
            "Preferred time",
            value=time(19, 0),
            step=1800,
        )

        submitted = st.form_submit_button(
            "Request reservation",
            type="primary",
        )

    if submitted:
        if not customer.strip():
            st.error("Please enter your name.")
        else:
            success, message = create_reservation(
                customer,
                int(guests),
                booking_date,
                booking_time,
            )

            if success:
                st.success(message)
            else:
                st.error(message)

# ==========================================
# RESTAURANT DASHBOARD
# ==========================================

elif page == "Restaurant Dashboard":
    st.title("Restaurant dashboard")
    st.caption("Demo dashboard — authentication not yet implemented.")

    with get_connection() as conn:
        total_orders = conn.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        total_reservations = conn.execute(
            "SELECT COUNT(*) FROM reservations "
            "WHERE status != 'Cancelled'"
        ).fetchone()[0]

        total_sales = conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM orders"
        ).fetchone()[0]

        orders = conn.execute("""
            SELECT id, customer, order_type, items,
                   total, status, created_at
            FROM orders
            ORDER BY id DESC
        """).fetchall()

        reservations = conn.execute("""
            SELECT id, customer, guests, booking_date,
                   booking_time, status
            FROM reservations
            ORDER BY booking_date DESC, booking_time DESC
        """).fetchall()

    col1, col2, col3 = st.columns(3)

    col1.metric("Total orders", total_orders)
    col2.metric("Reservations", total_reservations)
    col3.metric("Order sales", money(total_sales))

    st.divider()
    st.subheader("Recent orders")

    if orders:
        st.dataframe(
            [
                {
                    "Order ID": row[0],
                    "Customer": row[1],
                    "Type": row[2],
                    "Items": row[3],
                    "Total": money(row[4]),
                    "Status": row[5],
                    "Created": row[6],
                }
                for row in orders
            ],
            use_container_width=True,
            hide_index=True,
        )

        order_to_update = st.selectbox(
            "Select order to update",
            [row[0] for row in orders],
        )

        new_status = st.selectbox(
            "New order status",
            ["Pending", "Preparing", "Ready", "Completed", "Cancelled"],
        )

        if st.button("Update order status"):
            with get_connection() as conn:
                conn.execute("""
                    UPDATE orders
                    SET status = ?
                    WHERE id = ?
                """, (new_status, order_to_update))

            st.success("Order status updated.")
            st.rerun()

    else:
        st.info("No orders have been placed yet.")

    st.divider()
    st.subheader("Reservations")

    if reservations:
        st.dataframe(
            [
                {
                    "Booking ID": row[0],
                    "Customer": row[1],
                    "Guests": row[2],
                    "Date": row[3],
                    "Time": row[4],
                    "Status": row[5],
                }
                for row in reservations
            ],
            use_container_width=True,
            hide_index=True,
        )

        reservation_to_update = st.selectbox(
            "Select reservation",
            [row[0] for row in reservations],
        )

        reservation_status = st.selectbox(
            "Reservation status",
            ["Pending", "Confirmed", "Cancelled"],
        )

        if st.button("Update reservation"):
            with get_connection() as conn:
                conn.execute("""
                    UPDATE reservations
                    SET status = ?
                    WHERE id = ?
                """, (reservation_status, reservation_to_update))

            st.success("Reservation status updated.")
            st.rerun()

    else:
        st.info("No reservations have been submitted yet.")

    st.divider()
    st.subheader("Menu availability")

    all_menu = fetch_menu(available_only=False)

    if all_menu:
        for item in all_menu:
            item_id, name, category, price, available = item

            col1, col2, col3 = st.columns([3, 1, 1])

            col1.write(f"{name} — {money(price)}")
            col2.write("Available" if available else "Unavailable")

            with col3:
                if available:
                    if st.button("Mark unavailable", key=f"off_{item_id}"):
                        with get_connection() as conn:
                            conn.execute("""
                                UPDATE menu
                                SET available = 0
                                WHERE id = ?
                            """, (item_id,))

                        st.rerun()
                else:
                    if st.button("Mark available", key=f"on_{item_id}"):
                        with get_connection() as conn:
                            conn.execute("""
                                UPDATE menu
                                SET available = 1
                                WHERE id = ?
                            """, (item_id,))

                        st.rerun()

    st.caption(
        "This is a portfolio prototype, not yet a production-ready "
        "restaurant system. Authentication, real table allocation, "
        "delivery addresses, payments, backups, and WhatsApp integration "
        "remain future development tasks."
    )