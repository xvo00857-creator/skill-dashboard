import argparse
import sys

def main():
    sys.stdout.reconfigure(encoding='utf-8', newline='\n')
    parser = argparse.ArgumentParser(description='Get the next page URL from the Hacker News "More" link.')
    args = parser.parse_args()

    js = f"""
    (function() {{
      try {{
        var more = document.querySelector('a.morelink');
        if (!more) {{
          return JSON.stringify({{ hasNext: false, nextUrl: null, message: 'No morelink found; reached the last available page.' }});
        }}
        return JSON.stringify({{ hasNext: true, nextUrl: more.href }});
      }} catch(e) {{
        return JSON.stringify({{ error: true, message: e.message }});
      }}
    }})()
    """
    print(js)

if __name__ == '__main__':
    main()
