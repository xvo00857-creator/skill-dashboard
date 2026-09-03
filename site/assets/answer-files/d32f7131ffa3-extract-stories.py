import argparse
import sys

def main():
    sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    parser = argparse.ArgumentParser(description='Extract front-page stories from the current Hacker News page DOM.')
    parser.add_argument('--limit', type=int, default=0, help='Maximum number of stories to return; 0 means no limit.')
    args = parser.parse_args()

    js = f"""
    (function() {{
      try {{
        var limit = {args.limit};
        var rows = document.querySelectorAll('tr.athing.submission');
        if (!rows || rows.length === 0) {{
          return JSON.stringify({{ error: true, message: 'No story rows found. The page structure may have changed or the page has not finished loading.' }});
        }}
        var items = Array.prototype.map.call(rows, function(row) {{
          var id = row.id || null;
          var rankEl = row.querySelector('.rank');
          var titleEl = row.querySelector('.titleline > a');
          var siteEl = row.querySelector('.sitestr');
          var subtextRow = row.nextElementSibling;
          var subtext = subtextRow ? subtextRow.querySelector('.subtext, .subline') : null;
          var scoreEl = subtext ? subtext.querySelector('.score') : null;
          var userEl = subtext ? subtext.querySelector('.hnuser') : null;
          var ageEl = subtext ? subtext.querySelector('.age a') : null;
          var commentsEl = null;
          if (subtext) {{
            var itemLinks = subtext.querySelectorAll('a[href^="item?id="]');
            if (itemLinks.length > 0) commentsEl = itemLinks[itemLinks.length - 1];
          }}
          var score = null;
          if (scoreEl) {{
            var sm = scoreEl.textContent.match(/(\\d+)/);
            score = sm ? parseInt(sm[1], 10) : null;
          }}
          var comments = null;
          if (commentsEl) {{
            var cm = commentsEl.textContent.match(/(\\d+)/);
            comments = cm ? parseInt(cm[1], 10) : 0;
          }}
          var rank = null;
          if (rankEl) {{
            var rm = rankEl.textContent.match(/(\\d+)/);
            rank = rm ? parseInt(rm[1], 10) : null;
          }}
          return {{
            id: id,
            rank: rank,
            title: titleEl ? titleEl.textContent.trim() : null,
            url: titleEl ? titleEl.href : null,
            site: siteEl ? siteEl.textContent.trim() : null,
            score: score,
            user: userEl ? userEl.textContent.trim() : null,
            age: ageEl ? ageEl.textContent.trim() : null,
            comments: comments
          }};
        }});
        if (limit > 0) items = items.slice(0, limit);
        return JSON.stringify({{ count: items.length, items: items }});
      }} catch(e) {{
        return JSON.stringify({{ error: true, message: e.message }});
      }}
    }})()
    """
    print(js)

if __name__ == '__main__':
    main()
