PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS locations (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  short_name TEXT NOT NULL,
  address TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
  id TEXT PRIMARY KEY,
  location_id TEXT NOT NULL REFERENCES locations(id),
  class_type TEXT NOT NULL,
  name TEXT NOT NULL,
  coach TEXT,
  starts_at TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL DEFAULT 50,
  capacity INTEGER NOT NULL CHECK(capacity > 0),
  reserved_count INTEGER NOT NULL DEFAULT 0 CHECK(reserved_count >= 0),
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','cancelled','hidden')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_classes_start_location ON classes(starts_at, location_id);

CREATE TABLE IF NOT EXISTS customers (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  first_name TEXT,
  last_name TEXT,
  phone TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
  id TEXT PRIMARY KEY,
  reference TEXT NOT NULL UNIQUE,
  class_id TEXT NOT NULL REFERENCES classes(id),
  customer_id TEXT REFERENCES customers(id),
  email TEXT NOT NULL,
  first_name TEXT,
  status TEXT NOT NULL DEFAULT 'reserved' CHECK(status IN ('reserved','cancelled','attended','no_show')),
  payment_state TEXT NOT NULL DEFAULT 'not_required' CHECK(payment_state IN ('not_required','pending','paid','failed','refunded')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  cancelled_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_bookings_email ON bookings(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bookings_class ON bookings(class_id, status);

CREATE TRIGGER IF NOT EXISTS booking_capacity_guard
BEFORE INSERT ON bookings
WHEN NEW.status = 'reserved'
BEGIN
  SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM classes WHERE id = NEW.class_id AND status = 'active') THEN RAISE(ABORT, 'CLASS_NOT_AVAILABLE')
    WHEN (SELECT reserved_count >= capacity FROM classes WHERE id = NEW.class_id) THEN RAISE(ABORT, 'CLASS_FULL')
    WHEN EXISTS (SELECT 1 FROM bookings WHERE class_id = NEW.class_id AND lower(email) = lower(NEW.email) AND status = 'reserved') THEN RAISE(ABORT, 'DUPLICATE_BOOKING')
  END;
  UPDATE classes SET reserved_count = reserved_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = NEW.class_id;
END;

CREATE TRIGGER IF NOT EXISTS booking_cancel_release
AFTER UPDATE OF status ON bookings
WHEN OLD.status = 'reserved' AND NEW.status = 'cancelled'
BEGIN
  UPDATE classes SET reserved_count = MAX(0, reserved_count - 1), updated_at = CURRENT_TIMESTAMP WHERE id = NEW.class_id;
END;

CREATE TABLE IF NOT EXISTS waitlist (
  id TEXT PRIMARY KEY,
  class_id TEXT NOT NULL REFERENCES classes(id),
  email TEXT NOT NULL,
  first_name TEXT,
  position INTEGER,
  status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting','offered','converted','removed','expired')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_waitlist_class_status ON waitlist(class_id, status, created_at);

CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'class_pack',
  credits INTEGER,
  price_cents INTEGER NOT NULL,
  currency TEXT NOT NULL DEFAULT 'eur',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  reference TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  amount_cents INTEGER NOT NULL,
  currency TEXT NOT NULL DEFAULT 'eur',
  provider TEXT,
  provider_payment_id TEXT,
  payment_method TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','paid','failed','cancelled','refunded')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id TEXT NOT NULL,
  product_name TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  unit_price_cents INTEGER NOT NULL,
  credits INTEGER
);

CREATE TABLE IF NOT EXISTS credit_ledger (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  order_id TEXT REFERENCES orders(id),
  booking_id TEXT REFERENCES bookings(id),
  delta INTEGER NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_email ON credit_ledger(email, created_at DESC);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  key TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  response_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO locations(id,name,short_name,address) VALUES
('bhf1','Bahnhofsviertel · 1. OG','Bahnhofsviertel 1F','Kaiserstraße 61 · 60329 Frankfurt'),
('ladies','Bahnhofsviertel · Ladies','Ladies 2F','Kaiserstraße 61 · 60329 Frankfurt'),
('sachsen','Sachsenhausen','Sachsenhausen','Zum Gipelhof 5 · 60594 Frankfurt'),
('bornheim','Bornheim','Bornheim','Wiesenstraße 33 · 60385 Frankfurt'),
('mid','Mid','Mid','Große Eschenheimer Straße 45 · 60313 Frankfurt'),
('oval','Oval','Oval','Baseler Straße 10 · 60329 Frankfurt');

INSERT OR IGNORE INTO products(id,name,kind,credits,price_cents,currency) VALUES
('single','1 Class','class_pack',1,2800,'eur'),
('five','5 Classes','class_pack',5,11900,'eur'),
('ten','10 Classes','class_pack',10,21900,'eur'),
('twenty','20 Classes','class_pack',20,39900,'eur');