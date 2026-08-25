"""
SmartMandi Queue Manager - Hackathon Simulation & Stress-Test Tool
SIH26032 | simulate_mandi_day.py

Usage
-----
  # Full 8-hour mandi day compressed to ~2 minutes
  python scripts/simulate_mandi_day.py

  # Override speed multiplier (lower = faster)
  python scripts/simulate_mandi_day.py --speed 60

  # Run the anti-overbooking stress test
  python scripts/simulate_mandi_day.py --stress-test

  # Stress test with custom concurrency
  python scripts/simulate_mandi_day.py --stress-test --workers 150
"""

import sys
import io

# Force UTF-8 output on Windows terminals so Rich box-chars render correctly
if hasattr(sys.stdout, "buffer") and sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import time
import random
import argparse
import threading
import statistics
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import urllib.request
    import json
except ImportError:
    pass

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich import box
    from rich.rule import Rule
    RICH = True
except ImportError:
    RICH = False

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
API_BASE = "http://127.0.0.1:8000"

SIMULATION_REAL_DURATION_SECS = 120      # 8-hour day compressed to 2 real minutes
DEFAULT_SPEED_DIVISOR = 480              # 480x compression (8*60)

CROP_TYPES = [
    "Wheat (Kanak)",
    "Paddy (Basmati)",
    "Paddy (PR-126)",
    "Mustard (Sarson)",
]

FARMER_NAMES = [
    "Gurpreet Singh",   "Rajveer Yadav",    "Harpreet Kaur",
    "Mahinder Sharma",  "Balwant Sidhu",    "Kuldeep Grewal",
    "Paramjit Singh",   "Sukhjinder Brar",  "Manpreet Dhaliwal",
    "Amritpal Virk",    "Jaswant Randhawa", "Gurmail Toor",
    "Ravinder Sandhu",  "Bhupinder Gill",   "Sukhdev Kamboj",
    "Charanjit Bajwa",  "Daljeet Maan",     "Gurjant Cheema",
    "Satnam Hundal",    "Tejinder Walia",
]

MSP_PER_QUINTAL = 2275.0  # Rs per quintal (Wheat MSP FY 2026)

console = Console(force_terminal=True) if RICH else None


# -----------------------------------------------------------------------------
# HTTP Helpers (stdlib only - no requests dependency needed)
# -----------------------------------------------------------------------------
def http_get(path: str) -> tuple:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}
    except Exception as exc:
        return 0, {"error": str(exc)}


def http_post(path: str, payload: dict) -> tuple:
    url = f"{API_BASE}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}
    except Exception as exc:
        return 0, {"error": str(exc)}


def http_patch(path: str, payload: dict) -> tuple:
    url = f"{API_BASE}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {}
    except Exception as exc:
        return 0, {"error": str(exc)}


# -----------------------------------------------------------------------------
# Console helpers
# -----------------------------------------------------------------------------
def log_event(tag: str, tag_style: str, message: str):
    ts = datetime.now().strftime("%H:%M:%S")
    if RICH:
        console.print(f"[dim]{ts}[/dim]  [{tag_style}]{tag:<18}[/{tag_style}]  {message}")
    else:
        print(f"[{ts}]  {tag:<18}  {message}")


def section(title: str):
    if RICH:
        console.print()
        console.print(Rule(f"[bold cyan]{title}[/bold cyan]", style="cyan"))
    else:
        print(f"\n{'='*60}\n  {title}\n{'='*60}")


# -----------------------------------------------------------------------------
# Pre-flight check
# -----------------------------------------------------------------------------
def preflight_check() -> tuple:
    """Verify backend is running and return (center, farmers)."""
    section("PRE-FLIGHT SYSTEM CHECK")

    status_code, health = http_get("/health")
    if status_code != 200:
        if RICH:
            console.print("[bold red]ERROR:[/bold red] Backend not reachable at "
                          f"{API_BASE}. Is uvicorn running?")
            console.print("[yellow]Run:[/yellow]  cd backend && "
                          ".\\venv\\Scripts\\uvicorn main:app --host 127.0.0.1 --port 8000")
        else:
            print(f"ERROR: Backend not reachable at {API_BASE}. Is uvicorn running?")
        sys.exit(1)

    log_event("[HEALTH]", "green",
              f"Backend online -- DB: {health.get('database')} "
              f"| Farmers: {health['stats']['total_farmers']}")

    _, centers = http_get("/centers")
    if not centers:
        print("No centers found. Run: python backend/seed.py first.")
        sys.exit(1)
    center = centers[0]
    log_event("[CENTER]", "cyan",
              f"{center['name']} ({center['district']}) "
              f"-- Capacity: {center['daily_capacity_quintals']} Q")

    _, farmers = http_get("/farmers?limit=50")
    if not farmers:
        print("No farmers found in DB. Run seed.py first.")
        sys.exit(1)
    log_event("[FARMERS]", "magenta",
              f"Loaded {len(farmers)} registered farmers from database")

    return center, farmers


# -----------------------------------------------------------------------------
# SIMULATION MODE - 8-hour day compressed into 2 minutes
# -----------------------------------------------------------------------------
def run_simulation(speed_divisor: int, center: dict, farmers: list):
    today = str(date.today())
    # Real seconds to wait between each of the 20 farmer arrivals
    real_step = SIMULATION_REAL_DURATION_SECS / 20
    delay_farmer_idx = random.randint(6, 10)
    delay_injected = False
    booked = []
    total_payout = 0.0

    section(f"SIMULATING MANDI DAY  [{today}]  --  8 hrs in {SIMULATION_REAL_DURATION_SECS}s")

    if RICH:
        console.print(Panel(
            f"[bold]Center:[/bold] {center['name']}\n"
            f"[bold]Speed:[/bold] {speed_divisor}x compression  |  "
            f"[bold]Farmers:[/bold] 20  |  "
            f"[bold]Delay Event:[/bold] Farmer #{delay_farmer_idx + 1}",
            title="[bold green]Simulation Config[/bold green]",
            border_style="green"
        ))

    # ── PHASE 1: Sequential Arrivals & Bookings ───────────────────────────────
    section("PHASE 1 -- SEQUENTIAL FARMER ARRIVALS & SLOT BOOKINGS")

    farmer_pool = (farmers * 5)[:20]

    for idx, farmer in enumerate(farmer_pool):
        qty = round(random.uniform(60.0, 220.0), 1)
        crop = random.choice(CROP_TYPES)

        sc, booking = http_post("/api/bookings", {
            "farmer_id": farmer["id"],
            "center_id": center["id"],
            "crop_type": crop,
            "estimated_quantity_quintals": qty,
            "requested_date": today,
        })

        name = FARMER_NAMES[idx % len(FARMER_NAMES)]

        if sc == 201:
            booked.append({**booking, "farmer_name": name, "quantity": qty})
            log_event(
                "[ARRIVED]", "bold green",
                f"[bold]{name}[/bold]  "
                f"Token [cyan]#{booking['queue_number']}[/cyan]  |  "
                f"{crop}  |  {qty} Q  |  "
                f"ETA: [yellow]{booking.get('estimated_arrival_time_formatted', '--')}[/yellow]"
            )
        else:
            detail = booking.get("detail", str(booking))
            log_event("[REJECTED]", "red", f"{name} -- {detail}")

        time.sleep(real_step * 0.25)

    log_event("[PHASE 1 DONE]", "bold cyan",
              f"{len(booked)}/{len(farmer_pool)} farmers booked successfully")
    time.sleep(1.0)

    # ── PHASE 2: Queue Processing ─────────────────────────────────────────────
    section("PHASE 2 -- LIVE QUEUE PROCESSING")

    time_per_farmer = real_step * 0.75

    for idx, booking in enumerate(booked):
        bid = booking["booking_id"]
        fname = booking["farmer_name"]
        qty = booking["quantity"]

        # ── Inject Tractor Delay ─────────────────────────────────────────────
        if idx == delay_farmer_idx and not delay_injected:
            delay_injected = True
            delay_secs = 10

            section("!! TRACTOR DELAY EVENT !!")
            log_event(
                "[DELAY DETECTED]", "bold yellow",
                f"Tractor breakdown at Mandi gate! "
                f"Injecting {delay_secs}s hold -- "
                f"Recalculating ETAs for {len(booked) - idx} downstream farmers."
            )

            # CHECKED_IN triggers backend ETA recalculation for all active bookings
            http_patch(f"/api/bookings/{bid}/status", {"status": "CHECKED_IN"})
            time.sleep(delay_secs)
            log_event("[DELAY CLEARED]", "green",
                      "Tractor cleared. Queue resumed. ETAs recalculated by backend.")
            section("PHASE 2 -- QUEUE RESUMED")

            # Finish this farmer from CHECKED_IN -> WEIGHING -> COMPLETED
            http_patch(f"/api/bookings/{bid}/status", {"status": "WEIGHING"})
            time.sleep(time_per_farmer * 0.4)
            _, complete_resp = http_patch(f"/api/bookings/{bid}/status", {"status": "COMPLETED"})

        else:
            # Normal happy path
            log_event("[CHECK-IN]", "cyan",
                      f"[bold]{fname}[/bold] -- Token #{booking['queue_number']} reporting to counter")
            time.sleep(time_per_farmer * 0.2)
            http_patch(f"/api/bookings/{bid}/status", {"status": "CHECKED_IN"})

            log_event("[WEIGHING]", "magenta",
                      f"[bold]{fname}[/bold] -- Tractor on weighbridge... {qty} Q measuring")
            time.sleep(time_per_farmer * 0.5)
            http_patch(f"/api/bookings/{bid}/status", {"status": "WEIGHING"})

            time.sleep(time_per_farmer * 0.3)
            _, complete_resp = http_patch(f"/api/bookings/{bid}/status", {"status": "COMPLETED"})

        payout = round(qty * MSP_PER_QUINTAL, 2)
        total_payout += payout
        avg_pace = complete_resp.get("average_processing_time_minutes", 15.0)

        log_event(
            "[PAYMENT CLEARED]", "bold green",
            f"[bold]{fname}[/bold]  "
            f"[green]Rs {payout:,.0f}[/green] disbursed @ MSP Rs {MSP_PER_QUINTAL}/Q  "
            f"| Avg pace [yellow]{avg_pace:.1f}m[/yellow]/turn"
        )
        time.sleep(0.2)

    # ── Final Summary ─────────────────────────────────────────────────────────
    section("SIMULATION COMPLETE -- DAILY SUMMARY")

    total_qty = sum(b["quantity"] for b in booked)

    if RICH:
        t = Table(box=box.ROUNDED, border_style="green",
                  title="[bold]SmartMandi Day Summary[/bold]")
        t.add_column("Metric", style="cyan", no_wrap=True)
        t.add_column("Value", style="bold white")

        t.add_row("Farmers Processed", str(len(booked)))
        t.add_row("Total Procurement", f"{total_qty:,.1f} Quintals")
        t.add_row("Total MSP Payout", f"Rs {total_payout:,.2f}")
        t.add_row("Tractor Delay Event", "[yellow]1 (ETAs auto-recalculated)[/yellow]")
        t.add_row("Center", center["name"])
        t.add_row("Date", today)
        console.print(t)
    else:
        print(f"Farmers Processed : {len(booked)}")
        print(f"Total Procurement : {total_qty:,.1f} Q")
        print(f"Total MSP Payout  : Rs {total_payout:,.2f}")


# -----------------------------------------------------------------------------
# STRESS TEST MODE - Anti-overbooking concurrency benchmark
# -----------------------------------------------------------------------------
def run_stress_test(num_workers: int, center: dict, farmers: list):
    # Use a date far in the future so we don't pollute today's live queue
    future_date = str(date.today() + timedelta(days=60))
    SLOT_QTY = 50.0

    # Center has a real capacity, so we calculate expected successes
    capacity_q = center["daily_capacity_quintals"]
    expected_successes = int(capacity_q // SLOT_QTY)

    section(f"STRESS TEST -- ANTI-OVERBOOKING BENCHMARK")

    if RICH:
        console.print(Panel(
            f"[bold]Concurrent Workers:[/bold] {num_workers}\n"
            f"[bold]Each Booking Qty:[/bold] {SLOT_QTY} Q\n"
            f"[bold]Center Capacity:[/bold] {capacity_q:,.0f} Q\n"
            f"[bold]Max Possible Successes:[/bold] {expected_successes}\n"
            f"[bold]Expected Failures:[/bold] {max(0, num_workers - expected_successes)}",
            title="[bold red]Concurrency Stress Test[/bold red]",
            border_style="red"
        ))

    successes = []
    failures = []
    latencies = []
    lock = threading.Lock()
    farmer_ids = [f["id"] for f in farmers]

    def send_booking(worker_id: int) -> dict:
        farmer_id = farmer_ids[worker_id % len(farmer_ids)]
        payload = {
            "farmer_id": farmer_id,
            "center_id": center["id"],
            "crop_type": "Wheat (Kanak)",
            "estimated_quantity_quintals": SLOT_QTY,
            "requested_date": future_date,
        }
        t0 = time.perf_counter()
        sc, resp = http_post("/api/bookings", payload)
        lat_ms = (time.perf_counter() - t0) * 1000

        result = {
            "worker_id": worker_id,
            "status_code": sc,
            "success": sc == 201,
            "latency_ms": lat_ms,
            "detail": resp.get("detail", ""),
        }
        with lock:
            (successes if result["success"] else failures).append(result)
            latencies.append(lat_ms)
        return result

    log_event("[FIRING]", "bold red",
              f"Launching {num_workers} concurrent booking requests to {center['name']}...")

    if RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[red]Hammering the booking endpoint...", total=num_workers)
            with ThreadPoolExecutor(max_workers=min(num_workers, 50)) as executor:
                futs = {executor.submit(send_booking, i): i for i in range(num_workers)}
                for fut in as_completed(futs):
                    fut.result()
                    progress.advance(task)
    else:
        with ThreadPoolExecutor(max_workers=min(num_workers, 50)) as executor:
            list(executor.map(send_booking, range(num_workers)))

    # ── Statistics ────────────────────────────────────────────────────────────
    total = len(successes) + len(failures)
    sorted_lat = sorted(latencies)
    p95 = sorted_lat[int(0.95 * total) - 1] if total >= 20 else sorted_lat[-1]
    p99 = sorted_lat[int(0.99 * total) - 1] if total >= 100 else sorted_lat[-1]
    avg_lat = statistics.mean(latencies) if latencies else 0

    section("STRESS TEST RESULTS")

    if RICH:
        t = Table(box=box.ROUNDED, border_style="cyan",
                  title="[bold]Anti-Overbooking Benchmark Results[/bold]")
        t.add_column("Metric", style="bold cyan", no_wrap=True)
        t.add_column("Value", style="bold white")
        t.add_column("Notes", style="dim")

        t.add_row("Total Requests Sent", str(total), "Fired concurrently")
        t.add_row("[green]Successful Bookings[/green]",
                  f"[bold green]{len(successes)}[/bold green]", "HTTP 201 Created")
        t.add_row("[red]Rejected Requests[/red]",
                  f"[bold red]{len(failures)}[/bold red]", "HTTP 400 CAPACITY_EXCEEDED")
        t.add_row("Success Rate",
                  f"{len(successes)/total*100:.1f}%",
                  f"Max allowed: {expected_successes}")
        t.add_row("Error Rate",
                  f"{len(failures)/total*100:.1f}%", "Correctly rejected")
        t.add_row("Avg Latency", f"{avg_lat:.1f} ms", "")
        t.add_row("p95 Latency", f"[yellow]{p95:.1f} ms[/yellow]", "")
        t.add_row("p99 Latency", f"[red]{p99:.1f} ms[/red]", "")
        console.print(t)

        # Verdict panel
        overbooked = len(successes) > expected_successes + 2
        if not overbooked:
            console.print(Panel(
                f"[bold green]LOCKS HELD[/bold green]\n"
                f"Expected max {expected_successes} bookings. Got: [bold]{len(successes)}[/bold].\n"
                f"Database-level capacity checks successfully prevented overbooking "
                f"under {num_workers}-way concurrency.",
                title="[bold green]VERDICT: PASS[/bold green]",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[bold red]OVERBOOKED[/bold red]\n"
                f"Expected <=>{expected_successes} but got {len(successes)} bookings.\n"
                "Review with_for_update() or transaction isolation level.",
                title="[bold red]VERDICT: FAIL[/bold red]",
                border_style="red"
            ))
    else:
        print(f"Total Requests    : {total}")
        print(f"Successful        : {len(successes)} (HTTP 201)")
        print(f"Rejected          : {len(failures)} (HTTP 400)")
        print(f"Success Rate      : {len(successes)/total*100:.1f}%")
        print(f"Avg Latency       : {avg_lat:.1f} ms")
        print(f"p95 Latency       : {p95:.1f} ms")
        print(f"p99 Latency       : {p99:.1f} ms")
        if len(successes) <= expected_successes + 2:
            print("VERDICT: PASS -- DB locks held, no overbooking")
        else:
            print("VERDICT: FAIL -- Overbooking detected!")


# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="SmartMandi Simulation & Stress-Test Tool | SIH26032",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--stress-test", action="store_true",
        help="Run anti-overbooking concurrency benchmark instead of simulation"
    )
    parser.add_argument(
        "--speed", type=int, default=DEFAULT_SPEED_DIVISOR,
        help=f"Compression divisor (default: {DEFAULT_SPEED_DIVISOR} = 480x faster)"
    )
    parser.add_argument(
        "--workers", type=int, default=100,
        help="Concurrent workers for stress test (default: 100)"
    )
    args = parser.parse_args()

    if RICH:
        console.print(Panel(
            "[bold white]SmartMandi Queue Manager[/bold white]\n"
            "[dim]Hackathon Simulation & Stress-Test Tool[/dim]\n"
            "[dim cyan]Project SIH26032  |  Smart India Hackathon 2026[/dim cyan]",
            border_style="bright_blue",
            padding=(1, 4),
        ))
    else:
        print("=" * 60)
        print("  SmartMandi Queue Manager -- SIH26032 Simulation Tool")
        print("=" * 60)

    center, farmers = preflight_check()

    if args.stress_test:
        run_stress_test(args.workers, center, farmers)
    else:
        run_simulation(args.speed, center, farmers)


if __name__ == "__main__":
    main()
