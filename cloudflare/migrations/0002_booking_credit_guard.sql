DROP TRIGGER IF EXISTS booking_credit_guard;
CREATE TRIGGER booking_credit_guard
AFTER INSERT ON bookings
WHEN NEW.status = 'reserved' AND NEW.payment_state = 'paid'
BEGIN
  SELECT CASE
    WHEN COALESCE((SELECT SUM(delta) FROM credit_ledger WHERE lower(email)=lower(NEW.email)),0) <= 0
    THEN RAISE(ABORT, 'NO_CREDIT')
  END;
  INSERT INTO credit_ledger(id,email,booking_id,delta,reason)
  VALUES(lower(hex(randomblob(16))),lower(NEW.email),NEW.id,-1,'booking');
END;

DROP TRIGGER IF EXISTS booking_credit_refund;
CREATE TRIGGER booking_credit_refund
AFTER UPDATE OF status ON bookings
WHEN OLD.status='reserved' AND NEW.status='cancelled' AND OLD.payment_state='paid'
BEGIN
  INSERT INTO credit_ledger(id,email,booking_id,delta,reason)
  VALUES(lower(hex(randomblob(16))),lower(NEW.email),NEW.id,1,'booking_cancelled');
END;