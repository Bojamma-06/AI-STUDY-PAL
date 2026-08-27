# AI_app.py
# Single-file AI Study Pal — ONLY MCQs, Balanced Easy/Medium/Difficult
# Compatible with Python 3.11 / PythonAnywhere

from flask import Flask, render_template_string, request
import random
import io
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change_this_to_a_random_string'

# ---------------------------
# Helpers / Original small functions
# ---------------------------
def generate_study_plan(subject, hours):
    return f"You should study {subject} for {hours} hours. Try breaking it into {hours} study blocks with short breaks."

def summarize_text(text):
    text = (text or "").strip()
    if not text:
        return "No text provided."
    words = text.split()
    return " ".join(words[:80]) + ("..." if len(words) > 80 else "")

def extract_tips(subject):
    return f"Focus on core topics in {subject}. Revise regularly. Practice previous questions."

def generate_feedback(subject):
    messages = [
        f"Great effort! Your {subject} skills are improving!",
        f"Keep pushing — you're doing awesome in {subject}!",
        f"Fantastic progress! Stay consistent with {subject}."
    ]
    return random.choice(messages)

# ---------------------------
# Sentence splitting & classification
# ---------------------------
def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', (text or "").strip())
    return [s.strip() for s in sentences if s.strip()]

def classify_sentence(sent):
    wc = len(re.findall(r'\w+', sent))
    if wc <= 10:
        return 'easy'
    elif wc <= 20:
        return 'medium'
    else:
        return 'difficult'

# ---------------------------
# Distractor generation
# ---------------------------
def make_distractors_from_sentence(sent):
    tokens = re.findall(r"\w+|[^\w\s]", sent)
    distractors = []

    # shuffle words (if long enough)
    words = [t for t in re.findall(r"\w+", sent)]
    if len(words) > 4:
        shuffled = words[:]
        random.shuffle(shuffled)
        distractors.append(" ".join(shuffled))

    # append "not true" variant
    distractors.append(sent + " (not true)")

    # replace first token with placeholder
    if tokens:
        replaced = sent.replace(tokens[0], "Something else", 1)
        distractors.append(replaced)

    # shorten version
    if len(words) > 6:
        distractors.append(" ".join(words[: max(3, len(words)//2)]) + " ...")

    # small swap twist
    if len(words) > 3:
        w = words[:]
        i, j = random.sample(range(len(w)), 2)
        w[i], w[j] = w[j], w[i]
        distractors.append(" ".join(w))

    # dedupe and exclude identical to original
    out = []
    for d in distractors:
        ds = d.strip()
        if ds and ds != sent and ds not in out:
            out.append(ds)
    random.shuffle(out)
    return out[:3]

# ---------------------------
# Question generators (ONLY MCQs)
# ---------------------------
def generate_easy_question(subject, sent):
    question = f"According to the text, which of the following is correct about {subject}?\n\n{sent}"
    opts = [sent] + make_distractors_from_sentence(sent)
    while len(opts) < 4:
        opts.append(f"Not true about {subject}.")
    random.shuffle(opts)
    correct_index = opts.index(sent)
    answer = ['A','B','C','D'][correct_index]
    return question, opts, answer

def generate_medium_question(subject, sent):
    question = f"What is the main point of the following sentence about {subject}?\n\n{sent}"
    opts = [sent] + make_distractors_from_sentence(sent)
    while len(opts) < 4:
        opts.append(f"A related but incorrect statement about {subject}.")
    random.shuffle(opts)
    correct_index = opts.index(sent)
    answer = ['A','B','C','D'][correct_index]
    return question, opts, answer

def generate_difficult_question(subject, sent):
    question = f"Which inference best follows from the statement about {subject}?\n\n{sent}"
    opts = [sent] + make_distractors_from_sentence(sent)
    while len(opts) < 4:
        opts.append(f"The opposite conclusion about {subject}.")
    random.shuffle(opts)
    correct_index = opts.index(sent)
    answer = ['A','B','C','D'][correct_index]
    return question, opts, answer

# ---------------------------
# Balanced quiz generator (ONLY MCQs)
# ---------------------------
def generate_quiz(subject, text_content=None, min_total=3, max_total=5):
    # Prepare pools
    if not text_content or not text_content.strip():
        easy_pool = [f"{subject} has basic facts about its concepts."]
        medium_pool = [f"{subject} connects concepts in meaningful ways."]
        difficult_pool = [f"{subject} requires reasoning across multiple ideas."]
    else:
        sents = split_sentences(text_content)
        meaningful = [s for s in sents if len(s.split()) >= 4]
        if not meaningful:
            meaningful = [text_content.strip()]
        easy_pool = [s for s in meaningful if classify_sentence(s) == 'easy']
        medium_pool = [s for s in meaningful if classify_sentence(s) == 'medium']
        difficult_pool = [s for s in meaningful if classify_sentence(s) == 'difficult']

    total = random.randint(min_total, max_total)

    # target 1-2 per level
    e_target = min(2, max(1, total // 3))
    m_target = min(2, max(1, total // 3))
    d_target = min(2, max(1, total - (e_target + m_target)))

    def pick(pool, k):
        if not pool:
            return []
        k = min(k, len(pool))
        return random.sample(pool, k)

    selected = []
    selected += pick(easy_pool, e_target)
    selected += pick(medium_pool, m_target)
    selected += pick(difficult_pool, d_target)

    all_pools = easy_pool + medium_pool + difficult_pool
    remaining = [s for s in all_pools if s not in selected]
    while len(selected) < total and remaining:
        selected.append(remaining.pop(0))
    while len(selected) < total:
        selected.append(selected[-1] if selected else f"Key point in {subject}.")

    quiz = []
    for i, sent in enumerate(selected):
        level = classify_sentence(sent)
        if level == 'easy':
            qtext, opts, ans = generate_easy_question(subject, sent)
        elif level == 'medium':
            qtext, opts, ans = generate_medium_question(subject, sent)
        else:
            qtext, opts, ans = generate_difficult_question(subject, sent)

        # ensure unique options and length exactly 4
        opts_unique = []
        for o in opts:
            if o not in opts_unique:
                opts_unique.append(o)
        while len(opts_unique) < 4:
            opts_unique.append(f"Incorrect statement about {subject}.")
        opts_unique = opts_unique[:4]

        # find the correct option index (correct is the original sentence)
        try:
            correct_index = opts_unique.index(sent)
        except ValueError:
            # fallback: if original sentence not present (rare), assume opts[0] is correct
            correct_index = 0

        answer_letter = ['A','B','C','D'][correct_index]

        quiz.append({
            'id': f'gen{i+1}',
            'level': level,
            'question': qtext,
            'opt_a': opts_unique[0],
            'opt_b': opts_unique[1],
            'opt_c': opts_unique[2],
            'opt_d': opts_unique[3],
            'answer': answer_letter
        })

    random.shuffle(quiz)
    return quiz

# ---------------------------
# Routes
# ---------------------------
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        subject = request.form.get('subject','').strip()
        hours = request.form.get('hours','').strip()
        text = request.form.get('text','').strip()
        if not subject:
            return render_template_string(HOME_TEMPLATE, error="Please enter a subject.")

        study_plan = generate_study_plan(subject, hours)
        summary = summarize_text(text)
        tips = extract_tips(subject)
        feedback = generate_feedback(subject)
        quiz_items = generate_quiz(subject, text_content=text, min_total=3, max_total=5)

        return render_template_string(QUIZ_TEMPLATE,
                                      subject=subject,
                                      hours=hours,
                                      study_plan=study_plan,
                                      summary=summary,
                                      tips=tips,
                                      feedback=feedback,
                                      quiz_items=quiz_items,
                                      timer_seconds=180)
    return render_template_string(HOME_TEMPLATE, error=None)

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    subject = request.form.get('subject','')
    hours = request.form.get('hours','')
    text = request.form.get('text','')

    answers = {}
    correct_answers = {}
    question_texts = {}
    option_texts = {}
    for key, val in request.form.items():
        if key.startswith('q_'):
            qid = key[2:]
            answers[qid] = val
        elif key.startswith('answer_'):
            qid = key[7:]
            correct_answers[qid] = val
        elif key.startswith('text_'):
            qid = key[5:]
            question_texts[qid] = val
        elif key.startswith('opt_'):
            m = re.match(r"opt_(.+)_(A|B|C|D)$", key)
            if m:
                qid = m.group(1)
                letter = m.group(2)
                option_texts.setdefault(qid, {})[letter] = val

    total = len(answers)
    score = 0
    details = []

    for qid, chosen_letter in answers.items():
        correct_letter = correct_answers.get(qid, chosen_letter)
        chosen_text = option_texts.get(qid, {}).get(chosen_letter, chosen_letter)
        correct_text = option_texts.get(qid, {}).get(correct_letter, correct_letter)
        qtext = question_texts.get(qid, qid)
        is_correct = (chosen_letter == correct_letter)
        details.append((qtext, chosen_text, correct_text, is_correct))
        if is_correct:
            score += 1

    img_bytes = create_score_plot(score, total)
    data64 = base64.b64encode(img_bytes).decode('utf-8')
    img_data_uri = 'data:image/png;base64,' + data64

    study_plan = generate_study_plan(subject, hours)
    summary = summarize_text(text)
    tips = extract_tips(subject)
    feedback = generate_feedback(subject)

    return render_template_string(RESULT_TEMPLATE,
                                  subject=subject,
                                  hours=hours,
                                  study_plan=study_plan,
                                  summary=summary,
                                  tips=tips,
                                  feedback=feedback,
                                  score=score,
                                  total=total,
                                  details=details,
                                  score_plot_uri=img_data_uri)

# ---------------------------
# Score plot
# ---------------------------
def create_score_plot(score, total):
    fig, axs = plt.subplots(1,2,figsize=(6,3), dpi=100)
    axs[0].bar(['Score','Remaining'], [score, max(0,total-score)], color=['#7fbf7f','#e9e9e9'])
    axs[0].set_ylim(0,max(1,total))
    axs[0].set_title('Score')
    labels = ['Correct','Incorrect']
    axs[1].pie([score,max(0,total-score)], labels=labels, autopct='%1.0f%%')
    axs[1].set_title('Result Breakdown')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf.read()

# ---------------------------
# Templates (pastel UI)
# ---------------------------
HOME_TEMPLATE = """<!doctype html>
<html>
<head>
  <title>AI Study Pal — Home</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    :root {--bg:#f6f9fb;--card:#fff;--accent:#7aa7ff;--muted:#7d8aa3;--soft:#eaf3ff;--radius:12px}
    body{font-family:Inter, Arial, sans-serif;background:var(--bg);margin:0;padding:28px;color:#223}
    .container{max-width:980px;margin:0 auto}
    .card{background:var(--card);padding:22px;border-radius:var(--radius);box-shadow:0 6px 18px rgba(18,38,63,0.06);margin-bottom:18px}
    h1{margin:0 0 8px 0;color:#113}
    label{display:block;margin-top:12px;font-weight:600;color:var(--muted)}
    input[type="text"], input[type="number"], textarea{width:100%;padding:10px;border-radius:10px;border:1px solid #e3edf7;background:var(--soft);margin-top:6px;box-sizing:border-box}
    button{background:var(--accent);color:#fff;padding:10px 16px;border:none;border-radius:10px;font-weight:700;cursor:pointer;margin-top:14px;box-shadow:0 6px 16px rgba(122,167,255,0.18)}
    .hint{color:var(--muted);font-size:0.95rem}
    footer{font-size:0.9rem;color:var(--muted);text-align:center;margin-top:6px}
    .error{color:#d9534f}
    @media (max-width:600px){body{padding:12px}}
  </style>
</head>
<body>
<div class="container">
  <div class="card">
    <h1>AI Study Pal</h1>
    <p class="hint">Paste a paragraph or notes below — the app will generate a balanced 3–5 question MCQ quiz (Easy / Medium / Difficult).</p>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="POST">
      <label>Subject</label>
      <input name="subject" placeholder="e.g. Biology, Algorithms" required>
      <label>Hours (for study plan)</label>
      <input name="hours" type="number" min="1" value="2" required>
      <label>Text / Notes (optional)</label>
      <textarea name="text" rows="8" placeholder="Paste textbook excerpt, lecture notes or summary..."></textarea>
      <button type="submit">Generate Study Plan & Take Quiz</button>
    </form>
  </div>
  <footer>Balanced quizzes — Auto easy/medium/difficult. No internet required.</footer>
</div>
</body>
</html>"""

QUIZ_TEMPLATE = """<!doctype html>
<html>
<head>
  <title>AI Study Pal — Quiz</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    :root{--bg:#f7fbfa; --card:#fff; --accent:#7aa7ff; --muted:#6b7684; --radius:12px}
    body{font-family:Inter, Arial, sans-serif;background:var(--bg);padding:14px;color:#123}
    .wrap{max-width:980px;margin:0 auto}
    .card{background:var(--card);padding:18px;border-radius:var(--radius);box-shadow:0 6px 18px rgba(17,34,51,0.06);margin-bottom:14px}
    h2{margin:0 0 8px 0}
    .progress{height:14px;background:#eef6ff;border-radius:10px;overflow:hidden;margin-bottom:12px}
    .progress > div{height:100%;background:var(--accent);width:0%}
    pre{white-space:pre-wrap;font-family:inherit;background:#f8fafc;padding:10px;border-radius:8px}
    label{display:block;margin-top:8px}
    .btn{background:var(--accent);color:#fff;padding:10px 14px;border-radius:10px;border:none;font-weight:700;cursor:pointer;margin-top:12px}
    .meta{color:var(--muted);font-size:0.95rem}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h2>Study Plan</h2>
      <p class="meta">{{ study_plan }}</p>
      <h3>Summary</h3>
      <p class="meta">{{ summary }}</p>
    </div>

    <div class="card">
      <h2>Quiz on "{{ subject }}"</h2>
      <p class="meta">Time left: <strong id="timer">--:--</strong></p>
      <div class="progress" aria-label="Quiz progress"><div id="progressbar"></div></div>

      <form method="POST" action="{{ url_for('submit_quiz') }}">
        <input type="hidden" name="subject" value="{{ subject }}">
        <input type="hidden" name="hours" value="{{ hours }}">
        <input type="hidden" name="text" value="{{ summary }}">
        {% for q in quiz_items %}
          <div style="margin-bottom:14px" class="card">
            <p><strong>Question {{ loop.index }} ({{ q.level|capitalize }})</strong></p>
            <pre>{{ q.question }}</pre>

            <label><input type="radio" name="q_{{ q.id }}" value="A" required> A. {{ q.opt_a }}</label>
            <label><input type="radio" name="q_{{ q.id }}" value="B"> B. {{ q.opt_b }}</label>
            <label><input type="radio" name="q_{{ q.id }}" value="C"> C. {{ q.opt_c }}</label>
            <label><input type="radio" name="q_{{ q.id }}" value="D"> D. {{ q.opt_d }}</label>

            <input type="hidden" name="opt_{{ q.id }}_A" value="{{ q.opt_a }}">
            <input type="hidden" name="opt_{{ q.id }}_B" value="{{ q.opt_b }}">
            <input type="hidden" name="opt_{{ q.id }}_C" value="{{ q.opt_c }}">
            <input type="hidden" name="opt_{{ q.id }}_D" value="{{ q.opt_d }}">
            <input type="hidden" name="answer_{{ q.id }}" value="{{ q.answer }}">
            <input type="hidden" name="text_{{ q.id }}" value="{{ q.question }}">
          </div>
        {% endfor %}

        <button class="btn" type="submit">Submit Answers</button>
      </form>
    </div>

    <div class="card">
      <h3>Tips</h3>
      <p class="meta">{{ tips }}</p>
      <h3>Motivation</h3>
      <p class="meta">{{ feedback }}</p>
    </div>
  </div>

<script>
let totalSeconds = {{ timer_seconds }};
let timerEl = document.getElementById('timer');
let progressEl = document.getElementById('progressbar');
let start = Date.now();
function updateTimer(){
    let elapsed = Math.floor((Date.now() - start) / 1000);
    let remain = totalSeconds - elapsed;
    if(remain < 0) remain = 0;
    let mins = String(Math.floor(remain/60)).padStart(2,'0');
    let secs = String(remain % 60).padStart(2,'0');
    timerEl.textContent = mins + ':' + secs;
    let pct = Math.min(100, Math.floor((elapsed/totalSeconds)*100));
    progressEl.style.width = pct + '%';
    if(elapsed >= totalSeconds){
        document.querySelector('form[action="{{ url_for('submit_quiz') }}"]').submit();
    } else {
        setTimeout(updateTimer, 500);
    }
}
updateTimer();
</script>
</body>
</html>"""

RESULT_TEMPLATE = """<!doctype html>
<html>
<head>
  <title>AI Study Pal — Results</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{font-family:Inter, Arial, sans-serif;background:#f7fbfb;padding:12px;color:#123}
    .card{background:#fff;padding:18px;border-radius:12px;max-width:980px;margin:12px auto;box-shadow:0 8px 22px rgba(10,30,60,0.06)}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{border:1px solid #eef3f7;padding:10px;text-align:left;vertical-align:top}
    pre{white-space:pre-wrap;font-family:inherit}
    a{display:inline-block;margin-top:12px;color:#2b6cff}
  </style>
</head>
<body>
  <div class="card">
    <h1>Results for {{ subject }}</h1>
    <p><strong>Score:</strong> {{ score }} / {{ total }}</p>
    <img src="{{ score_plot_uri }}" style="max-width:100%;height:auto">
    <h3>Details</h3>
    <table>
      <tr><th>Question</th><th>Your Answer</th><th>Correct Answer</th><th>Correct?</th></tr>
      {% for item in details %}
        <tr>
          <td><pre>{{ item[0] }}</pre></td>
          <td>{{ item[1] }}</td>
          <td>{{ item[2] }}</td>
          <td>{{ 'Yes' if item[3] else 'No' }}</td>
        </tr>
      {% endfor %}
    </table>

    <h3>Study Plan</h3>
    <p>{{ study_plan }}</p>

    <h3>Summary</h3>
    <p>{{ summary }}</p>

    <h3>Tips</h3>
    <p>{{ tips }}</p>

    <h3>Motivation</h3>
    <p>{{ feedback }}</p>

    <a href="{{ url_for('home') }}">Back to Home</a>
  </div>
</body>
</html>"""

# ---------------------------
# WSGI variable and run
# ---------------------------
application = app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
