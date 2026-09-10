from datetime import datetime, timedelta
import hashlib
import html
import re
import urllib.request
from flask import Flask, Response, request

URL = 'https://realit.shahaf.site/?cls=4&tab=exams'


app = Flask(__name__)

def escape_ics_text(text):
  """Escapes special characters for ICS text fields per RFC 5545."""
  if not text:
    return ''
  text = re.sub(r'[\r\n]+', ' ', text)
  text = text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
  return text.strip()


def generate_ics(append_text=""):
  req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
  with urllib.request.urlopen(req) as response:
    html_content = response.read().decode('utf-8')

  pattern = r'<li\s+class=["\']ChangesInfo["\'][^>]*>(.*?)<\/li>'
  matches = re.findall(pattern, html_content, re.DOTALL)

  ics_lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//School2Cal//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
  ]

  dtstamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')

  for item_html in matches:
    # Decode HTML entities (e.g., &quot; -> ", &amp; -> &)
    decoded_item = html.unescape(item_html)

    full_text = re.sub(r'<[^>]+>', '', decoded_item).strip()
    full_text = ' '.join(full_text.split())

    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', full_text)
    if not date_match:
      continue

    day, month, year = date_match.groups()
    start_date = f'{year}{month}{day}'

    current_date = datetime(int(year), int(month), int(day))
    end_date = (current_date + timedelta(days=1)).strftime('%Y%m%d')

    b_match = re.search(r'<b>(.*?)<\/b>', decoded_item)
    summary = (
        re.sub(r'<[^>]+>', '', b_match.group(1)).strip()
        if b_match
        else 'Schedule Change'
    )
    if append_text: summary = append_text+" "+summary
    description = full_text.replace(f'{day}.{month}.{year},', '').strip()

    uid_base = f'{start_date}-{summary}-{description}'
    uid = (
        hashlib.md5(uid_base.encode('utf-8')).hexdigest() + '@schedule-converter'
    )

    ics_lines.extend([
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{dtstamp}',
        f'DTSTART;VALUE=DATE:{start_date}',
        f'DTEND;VALUE=DATE:{end_date}',
        f'SUMMARY:{escape_ics_text(summary)}',
        f'DESCRIPTION:{escape_ics_text(description)}',
        'END:VEVENT',
    ])

  ics_lines.append('END:VCALENDAR')

#  filename = 'schedule_changes.ics'
#  with open(filename, 'w', encoding='utf-8') as f:
#    f.write('\n'.join(ics_lines))
  return ('\n'.join(ics_lines))
#  print(f'Successfully generated {filename} with {len(matches)} events.')


@app.route("/")
def calendar_feed():
  return Response(generate_ics(request.args.get('add')),mimetype='text/calendar',headers={'Content-Disposition': 'inline; filename="schedule.ics"'},)

if __name__ == '__main__':
#  print(generate_ics())
  app.run(host="0.0.0.0", port=5000)



