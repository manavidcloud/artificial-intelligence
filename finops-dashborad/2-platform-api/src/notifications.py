"""
Email notification module for the FinOps Platform API.

Supports cost spike alerts, daily digests, and budget threshold alerts.
Uses an HTML dark-theme / glassmorphism template consistent with the
FinOps dashboard UI.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared HTML fragments
# ---------------------------------------------------------------------------

_EMAIL_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 15px;
    line-height: 1.6;
    padding: 24px 16px;
  }}
  .wrapper {{
    max-width: 680px;
    margin: 0 auto;
  }}
  .header {{
    background: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.35);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 20px;
    backdrop-filter: blur(12px);
    text-align: center;
  }}
  .header .logo {{
    font-size: 13px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #818cf8;
    margin-bottom: 8px;
  }}
  .header h1 {{
    font-size: 24px;
    font-weight: 700;
    color: #f1f5f9;
  }}
  .card {{
    background: rgba(30, 32, 48, 0.75);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 16px;
    backdrop-filter: blur(8px);
  }}
  .card h2 {{
    font-size: 16px;
    font-weight: 600;
    color: #a5b4fc;
    margin-bottom: 14px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin-top: 8px;
  }}
  .stat-box {{
    background: rgba(99, 102, 241, 0.1);
    border: 1px solid rgba(99, 102, 241, 0.25);
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
  }}
  .stat-box .label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #94a3b8;
    margin-bottom: 4px;
  }}
  .stat-box .value {{
    font-size: 22px;
    font-weight: 700;
    color: #f1f5f9;
  }}
  .stat-box .value.danger {{ color: #f87171; }}
  .stat-box .value.warning {{ color: #fbbf24; }}
  .stat-box .value.success {{ color: #34d399; }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
  }}
  .badge.high {{ background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.35); }}
  .badge.medium {{ background: rgba(251,191,36,0.15); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }}
  .badge.low {{ background: rgba(52,211,153,0.15); color: #34d399; border: 1px solid rgba(52,211,153,0.3); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
  }}
  th {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b;
    text-align: left;
    padding: 6px 10px;
    border-bottom: 1px solid rgba(99,102,241,0.2);
  }}
  td {{
    padding: 8px 10px;
    color: #cbd5e1;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 13px;
  }}
  tr:last-child td {{ border-bottom: none; }}
  .divider {{
    border: none;
    border-top: 1px solid rgba(99,102,241,0.15);
    margin: 20px 0;
  }}
  .footer {{
    text-align: center;
    font-size: 12px;
    color: #475569;
    padding: 12px 0 0;
  }}
  .footer a {{ color: #818cf8; text-decoration: none; }}
  .alert-banner {{
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    font-weight: 600;
  }}
  .alert-banner.danger {{
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.4);
    color: #fca5a5;
  }}
  .alert-banner.warning {{
    background: rgba(251,191,36,0.12);
    border: 1px solid rgba(251,191,36,0.4);
    color: #fde68a;
  }}
  .progress-bar-bg {{
    background: rgba(255,255,255,0.08);
    border-radius: 9999px;
    height: 10px;
    overflow: hidden;
    margin-top: 6px;
  }}
  .progress-bar-fill {{
    height: 10px;
    border-radius: 9999px;
  }}
  .progress-bar-fill.danger {{ background: linear-gradient(90deg, #ef4444, #f87171); }}
  .progress-bar-fill.warning {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
  .progress-bar-fill.success {{ background: linear-gradient(90deg, #059669, #34d399); }}
</style>
</head>
<body>
<div class="wrapper">
"""

_EMAIL_FOOTER = """\
  <hr class="divider" />
  <div class="footer">
    Sent by <strong>FinOps Platform</strong> &bull;
    <a href="#">View Dashboard</a> &bull;
    Generated {timestamp}
  </div>
</div>
</body>
</html>
"""


def _wrap_email(title: str, body_html: str) -> str:
    head = _EMAIL_HEAD.format(title=title)
    footer = _EMAIL_FOOTER.format(timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    return head + body_html + footer


# ---------------------------------------------------------------------------
# EmailNotifier
# ---------------------------------------------------------------------------

class EmailNotifier:
    """Sends HTML email alerts via SMTP."""

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_addr = os.getenv("SMTP_FROM", self.user)
        raw = os.getenv("ALERT_RECIPIENTS", "")
        self.recipients = [r.strip() for r in raw.split(",") if r.strip()]

    def is_configured(self) -> bool:
        """Return True if all required SMTP settings are present."""
        return bool(self.host and self.user and self.password and self.recipients)

    def send(self, subject: str, html_body: str, recipients: list = None) -> bool:
        """Send a single HTML email. Returns True on success."""
        if not self.is_configured():
            logger.warning("EmailNotifier: not configured – skipping send.")
            return False

        to_list = recipients or self.recipients

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[FinOps Alert] {subject}"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(to_list)
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self.user, self.password)
                smtp.sendmail(self.from_addr, to_list, msg.as_string())

            logger.info("Email sent: '%s' → %s", subject, to_list)
            return True

        except Exception as exc:
            logger.error("Email failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Email template builders
    # ------------------------------------------------------------------

    def build_cost_spike_email(
        self,
        service: str,
        prev: float,
        curr: float,
        pct: float,
        currency: str = "USD",
    ) -> str:
        """Dark glassmorphism HTML email for a cost spike on a single service."""
        severity = "danger" if pct >= 100 else "warning"
        arrow = "▲"
        prev_fmt = f"{currency} {prev:,.2f}"
        curr_fmt = f"{currency} {curr:,.2f}"
        pct_fmt = f"+{pct:.1f}%"

        body = f"""
  <div class="header">
    <div class="logo">FinOps Platform</div>
    <h1>{arrow} Cost Spike Detected</h1>
  </div>

  <div class="alert-banner {severity}">
    <strong>{service}</strong> costs have increased by <strong>{pct_fmt}</strong>
    compared to the previous equivalent period.
  </div>

  <div class="card">
    <h2>Cost Comparison</h2>
    <div class="stat-grid">
      <div class="stat-box">
        <div class="label">Previous Period</div>
        <div class="value">{prev_fmt}</div>
      </div>
      <div class="stat-box">
        <div class="label">Current Period</div>
        <div class="value {severity}">{curr_fmt}</div>
      </div>
      <div class="stat-box">
        <div class="label">Change</div>
        <div class="value {severity}">{pct_fmt}</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Recommendations</h2>
    <table>
      <thead>
        <tr>
          <th>Action</th>
          <th>Details</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Review resource utilisation</td>
          <td>Check if recent deployments or workload changes caused the spike.</td>
        </tr>
        <tr>
          <td>Inspect scaling policies</td>
          <td>Verify auto-scaling limits and scheduled tasks for <strong>{service}</strong>.</td>
        </tr>
        <tr>
          <td>Check Advisor recommendations</td>
          <td>Azure Advisor may have right-sizing suggestions available.</td>
        </tr>
      </tbody>
    </table>
  </div>
"""
        return _wrap_email(f"Cost Spike – {service}", body)

    def build_daily_digest_email(
        self,
        total: float,
        currency: str,
        top_services: list,
        rec_count: int,
    ) -> str:
        """Daily digest email with total spend, top services, and recommendation count.

        Args:
            total: Total spend for the period.
            currency: Currency code (e.g. "USD").
            top_services: List of dicts with keys ``service_name`` and ``total_cost``.
            rec_count: Number of open Advisor Cost recommendations.
        """
        today = datetime.utcnow().strftime("%B %d, %Y")
        total_fmt = f"{currency} {total:,.2f}"

        rows_html = ""
        for rank, svc in enumerate(top_services[:10], start=1):
            name = svc.get("service_name", "Unknown")
            cost = float(svc.get("total_cost", 0))
            share = (cost / total * 100) if total else 0
            rows_html += f"""
        <tr>
          <td style="color:#94a3b8;">{rank}</td>
          <td>{name}</td>
          <td style="text-align:right;">{currency} {cost:,.2f}</td>
          <td style="text-align:right; color:#a5b4fc;">{share:.1f}%</td>
        </tr>"""

        body = f"""
  <div class="header">
    <div class="logo">FinOps Platform</div>
    <h1>Daily Cost Digest &ndash; {today}</h1>
  </div>

  <div class="card">
    <h2>Today&rsquo;s Snapshot</h2>
    <div class="stat-grid">
      <div class="stat-box">
        <div class="label">Total Spend</div>
        <div class="value">{total_fmt}</div>
      </div>
      <div class="stat-box">
        <div class="label">Services</div>
        <div class="value">{len(top_services)}</div>
      </div>
      <div class="stat-box">
        <div class="label">Advisor Recs</div>
        <div class="value {'warning' if rec_count > 0 else 'success'}">{rec_count}</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Top Services by Cost</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Service</th>
          <th style="text-align:right;">Cost</th>
          <th style="text-align:right;">Share</th>
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>Advisor Recommendations</h2>
    <p style="color:#94a3b8; font-size:13px;">
      There {"is" if rec_count == 1 else "are"} currently
      <strong style="color:#fbbf24;">{rec_count}</strong>
      open Cost recommendation{"s" if rec_count != 1 else ""} from Azure Advisor.
      Log in to the FinOps Dashboard to review and act on them.
    </p>
  </div>
"""
        return _wrap_email("Daily Cost Digest", body)

    def build_budget_alert_email(
        self,
        spent: float,
        budget: float,
        pct: float,
        currency: str = "USD",
        days_remaining: int = 0,
    ) -> str:
        """Budget threshold alert email.

        Args:
            spent: Amount spent so far in the billing period.
            budget: Total budget for the period.
            pct: Percentage of budget consumed (0-100+).
            currency: Currency code.
            days_remaining: Days left in the billing period.
        """
        if pct >= 100:
            severity = "danger"
            headline = "Budget Exceeded"
            status_color = "danger"
        elif pct >= 90:
            severity = "danger"
            headline = "Budget Critical (>90%)"
            status_color = "danger"
        elif pct >= 75:
            severity = "warning"
            headline = "Budget Warning (>75%)"
            status_color = "warning"
        else:
            severity = "warning"
            headline = "Budget Threshold Reached"
            status_color = "warning"

        remaining = max(budget - spent, 0)
        bar_width = min(int(pct), 100)
        daily_rate = (spent / max((30 - days_remaining), 1))
        projected = daily_rate * 30

        body = f"""
  <div class="header">
    <div class="logo">FinOps Platform</div>
    <h1>&#9888; {headline}</h1>
  </div>

  <div class="alert-banner {severity}">
    Your Azure spend has reached <strong>{pct:.1f}%</strong> of the monthly budget
    with <strong>{days_remaining}</strong> day{"s" if days_remaining != 1 else ""} remaining.
  </div>

  <div class="card">
    <h2>Budget Status</h2>
    <div class="stat-grid">
      <div class="stat-box">
        <div class="label">Spent</div>
        <div class="value {status_color}">{currency} {spent:,.2f}</div>
      </div>
      <div class="stat-box">
        <div class="label">Budget</div>
        <div class="value">{currency} {budget:,.2f}</div>
      </div>
      <div class="stat-box">
        <div class="label">Remaining</div>
        <div class="value {'danger' if remaining == 0 else 'success'}">{currency} {remaining:,.2f}</div>
      </div>
      <div class="stat-box">
        <div class="label">Projected Total</div>
        <div class="value {'danger' if projected > budget else 'warning'}">{currency} {projected:,.2f}</div>
      </div>
    </div>
    <div style="margin-top:16px;">
      <div style="display:flex; justify-content:space-between; font-size:12px; color:#94a3b8; margin-bottom:4px;">
        <span>0%</span>
        <span>{pct:.1f}% used</span>
        <span>100%</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill {status_color}" style="width:{bar_width}%;"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Recommended Actions</h2>
    <table>
      <thead>
        <tr>
          <th>Priority</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><span class="badge high">High</span></td>
          <td>Review the top spending services and identify reduction opportunities.</td>
        </tr>
        <tr>
          <td><span class="badge high">High</span></td>
          <td>Check Azure Advisor Cost recommendations for right-sizing options.</td>
        </tr>
        <tr>
          <td><span class="badge medium">Medium</span></td>
          <td>Evaluate reserved instance or savings plan purchases for predictable workloads.</td>
        </tr>
        <tr>
          <td><span class="badge low">Low</span></td>
          <td>Delete or deallocate idle resources to reduce ongoing spend.</td>
        </tr>
      </tbody>
    </table>
  </div>
"""
        return _wrap_email(headline, body)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

notifier = EmailNotifier()
