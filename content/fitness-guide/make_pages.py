#!/usr/bin/env python3
"""Generate src/*.html for the ARKive Fitness Guide (shared nav/footer). Usage: make_pages.py   Original text, MIT."""
import os
NAV = [("index.html","Home"),("safety.html","Start safely"),("calisthenics.html","Bodyweight"),("stretching.html","Stretching"),
       ("yoga.html","Yoga"),("breathing.html","Breathing"),("plans.html","Weekly plans"),("recovery.html","Recovery"),("cheatsheet.html","Cheat sheet")]
FOOT = ('<footer><p>ARKive Fitness Guide · original text, MIT licensed · general information for healthy people, not medical advice. '
        'If you have a heart, lung, joint or other condition, are pregnant, or are recovering from injury or surgery, ask a health professional what is safe for you.</p>'
        '<p class="mut">Background reading (not linked, this guide works offline): WHO physical activity guidelines (2020); US Physical Activity Guidelines for Americans, 2nd ed. (2018); NHS "Exercise" pages.</p></footer>')
def fig(lines):  # tiny stick figure: list of SVG path/circle snippets
    return f'<svg class="fig" viewBox="0 0 90 70" aria-hidden="true">{lines}</svg>'
F = {
 "pushup": fig('<circle cx="12" cy="40" r="5"/><path d="M17 42 L70 52 M28 44 L28 60 M70 52 L84 60"/>'),
 "squat": fig('<circle cx="40" cy="10" r="5"/><path d="M40 16 L36 38 L52 44 L50 62 M36 38 L26 52 L30 62 M40 22 L60 26"/>'),
 "plank": fig('<circle cx="12" cy="36" r="5"/><path d="M17 38 L76 50 M22 40 L22 58 L34 58 M76 50 L84 58"/>'),
 "bridge": fig('<circle cx="10" cy="58" r="5"/><path d="M16 58 L30 56 L50 38 L64 48 L68 62 M30 56 L28 62"/>'),
 "tree": fig('<circle cx="45" cy="8" r="5"/><path d="M45 14 L45 40 L45 64 M45 40 L56 48 L45 52 M45 20 L36 4 M45 20 L54 4"/>'),
 "child": fig('<circle cx="16" cy="56" r="5"/><path d="M22 54 L50 46 L66 58 L84 60 M50 46 L60 56 M22 58 L6 62"/>'),
 "dog": fig('<circle cx="22" cy="46" r="5"/><path d="M14 62 L44 16 L76 62 M28 42 L14 62"/>'),
}
P = {}
P["index.html"] = ("Fitness Guide", """<h1>Fitness Guide</h1><p>A short, plain-language guide to staying strong, flexible and calm with <b>no equipment</b>, in a small space. It suits beginners and people coming back to exercise. Everything here works offline.</p>
<div class="note"><b>Start here:</b> read <a href="safety.html">Start safely</a>, then try the <a href="plans.html">beginner week</a>. The <a href="cheatsheet.html">one-page cheat sheet</a> fits on a single printed page.</div>
<h2>Pages</h2><ul>
<li><a href="safety.html">Start safely</a>: warm-up, how hard to work, when to stop, cautions for older adults, pregnancy and injuries</li>
<li><a href="calisthenics.html">Bodyweight strength</a>: push-up progressions, squats, lunges, glute bridge, plank, chair dips, step-ups, burpees</li>
<li><a href="stretching.html">Stretching and mobility</a>: a 10-minute daily routine and a desk break routine</li>
<li><a href="yoga.html">Beginner yoga</a>: sun salutation and ten basic poses, described in words</li>
<li><a href="breathing.html">Breathing and meditation</a>: box breathing, slow breathing, body scan, simple mindfulness</li>
<li><a href="plans.html">Sample weekly plans</a>: beginner and intermediate, 15 to 30 minutes</li>
<li><a href="recovery.html">Recovery, sleep and water</a></li>
<li><a href="cheatsheet.html">Printable cheat sheet</a></li></ul>
<h2>The short version</h2><ul><li>Move a little every day; something is always better than nothing.</li><li>Aim over a week for about <b>150 minutes</b> of moderate activity (brisk walking counts) and <b>2 strength sessions</b>.</li><li>Start easier than you think, add a little each week.</li><li>Good form first, then more reps, then harder versions.</li><li>Sleep, water and rest days are part of training.</li></ul>""")
P["safety.html"] = ("Start safely", """<h1>Start safely</h1>
<h2>Before you begin</h2><p>Most people can safely start gentle exercise like walking and the beginner moves in this guide. Check with a health professional first if you have chest pain, heart disease, high blood pressure that is not controlled, diabetes, a lung condition, recent surgery or injury, dizziness or fainting, or if you are pregnant and new to exercise.</p>
<h2>Warm up (5 minutes)</h2><ol><li>March on the spot or walk briskly, 1 to 2 minutes.</li><li>Arm circles, 10 forward and 10 back.</li><li>Hip circles, 5 each way.</li><li>10 slow half squats.</li><li>10 gentle torso twists.</li><li>Leg swings holding a wall, 10 each leg.</li></ol>
<h2>How hard to work: the talk test</h2><table><tr><th>Effort</th><th>Talk test</th><th>Use for</th></tr><tr><td>Easy</td><td>You can sing</td><td>Warm-up, recovery days</td></tr><tr><td>Moderate</td><td>You can talk, not sing</td><td>Most of your training</td></tr><tr><td>Hard</td><td>Only a few words</td><td>Short bursts, intermediate only</td></tr></table>
<p>For strength moves, stop each set with <b>2 or 3 good reps left in the tank</b>. Mild muscle burn and next-day soreness are normal.</p>
<h2>Stop right away if you have</h2><ul><li>Chest pain, pressure or tightness</li><li>Unusual shortness of breath, dizziness, fainting or confusion</li><li>A racing or irregular heartbeat</li><li>Sharp, stabbing or joint pain (not ordinary muscle effort)</li><li>Numbness, tingling, or sudden weakness</li></ul><div class="note"><b>Chest pain that does not go away with rest is an emergency.</b> Get medical help.</div>
<h2>Older adults</h2><ul><li>Balance work matters as much as strength: practise standing on one leg near a wall or chair.</li><li>Use a sturdy chair for support; do squats as sit-to-stands.</li><li>Move slowly between lying, sitting and standing to avoid dizziness.</li></ul>
<h2>Pregnancy</h2><ul><li>If you were active before, you can usually keep going at a comfortable level; if new, start with walking and gentle moves. Check with your midwife or doctor.</li><li>After about the first trimester, avoid long periods lying flat on your back; do bridges and floor work on your side or propped up.</li><li>Avoid contact sports, risk of falls, overheating and holding your breath.</li><li>Stop and seek care for bleeding, fluid leaking, regular painful contractions, calf pain or swelling, or dizziness.</li></ul>
<h2>Injuries and sore joints</h2><ul><li>Work around an injury, not through it: train the parts that do not hurt.</li><li>Pain up to about 3 out of 10 that settles by the next day is usually fine; more than that, ease off.</li><li>Swelling, locking, or giving way of a joint needs a professional look.</li></ul>
<h2>Children and teens</h2><p>Kids need about an hour of active play a day. Bodyweight moves are fine for them with good form and no forcing; keep it playful.</p>""")
P["calisthenics.html"] = ("Bodyweight strength", f"""<h1>Bodyweight strength</h1><p>Do moves slowly and with control. Breathe out on the effort. <span class="lvl">B</span> beginner <span class="lvl">I</span> intermediate. Rest 30 to 90 seconds between sets.</p>
<h3>Push-up progressions</h3>{F['pushup']}<p>Hands just wider than shoulders, body in one straight line from head to heels, lower chest toward the surface, push back up.</p><ol><li>Wall push-up (hands on a wall)</li><li>Counter or table push-up</li><li>Knee push-up on the floor</li><li>Full push-up</li><li>Slow full push-up (3 seconds down) or feet on a step</li></ol><p><span class="lvl">B</span> 2 sets of 8 to 12 at the easiest level that feels challenging. <span class="lvl">I</span> 3 sets of 10 to 20; move up a level when you can do 3 sets of 15.</p>
<h3>Squat</h3>{F['squat']}<p>Feet shoulder width, sit hips back and down as if to a chair, knees follow toes, chest up, heels down. Stand up through the whole foot.</p><p><span class="lvl">B</span> sit-to-stand from a chair, 2 x 10. <span class="lvl">I</span> full squat 3 x 15 to 20, or pause 2 seconds at the bottom.</p>
<h3>Lunge</h3><p>Step one foot forward, lower until both knees bend about 90 degrees, front knee over the ankle, push back to standing. Hold a wall or chair for balance if needed.</p><p><span class="lvl">B</span> split squat (feet stay in place) 2 x 6 each leg. <span class="lvl">I</span> alternating or reverse lunges 3 x 10 each leg.</p>
<h3>Glute bridge</h3>{F['bridge']}<p>Lie on your back, knees bent, feet flat. Squeeze your buttocks and lift hips until knees, hips and shoulders line up. Pause, lower slowly.</p><p><span class="lvl">B</span> 2 x 12. <span class="lvl">I</span> single-leg bridge 3 x 8 each side.</p>
<h3>Plank</h3>{F['plank']}<p>Forearms under shoulders, body straight, squeeze stomach and buttocks, do not let hips sag. Breathe normally.</p><p><span class="lvl">B</span> on knees or hands on a table, 3 x 15 to 20 seconds. <span class="lvl">I</span> 3 x 30 to 60 seconds; add side planks.</p>
<h3>Chair dips</h3><p>Use a sturdy chair against a wall. Hands on the front edge, fingers forward, bend elbows straight back to about 90 degrees, push up. Keep shoulders down, away from ears. Skip if it hurts the front of your shoulder.</p><p><span class="lvl">B</span> knees bent, 2 x 6 to 8. <span class="lvl">I</span> legs straight, 3 x 10 to 15.</p>
<h3>Step-ups</h3><p>Use a stable step or the bottom stair. Step up with one foot, press through that heel to stand tall, step down slowly.</p><p><span class="lvl">B</span> low step, 2 x 8 each leg, holding a rail. <span class="lvl">I</span> higher step, 3 x 12 each leg.</p>
<h3>Burpees</h3><p>Squat, put hands on the floor, step or jump feet back to a plank, return feet, stand up (add a small jump if you like). This is hard on the heart; intermediate only.</p><p><span class="lvl">B</span> try "step-back burpees" with no jump, 2 x 5. <span class="lvl">I</span> 3 x 8 to 12, or 20 seconds on / 40 seconds off for 5 rounds.</p>
<h2>Making it harder over time</h2><ol><li>Add reps (up to the top of the range).</li><li>Add a set.</li><li>Slow the lowering part to 3 seconds.</li><li>Move to the next harder version and drop back to fewer reps.</li></ol>""")
P["stretching.html"] = ("Stretching and mobility", """<h1>Stretching and mobility</h1><p>Stretch when you are warm, for example after a walk or workout. Ease into a mild pull, never pain. Breathe slowly; hold each stretch <b>20 to 30 seconds</b>, both sides. Do not bounce.</p>
<h2>10-minute daily routine</h2><ol><li><b>Neck:</b> tilt ear toward shoulder, then chin toward chest.</li><li><b>Chest:</b> forearm on a doorframe, gently turn body away.</li><li><b>Upper back:</b> clasp hands in front, round your back and reach forward.</li><li><b>Cat and cow:</b> on hands and knees, slowly round then arch your back, 8 times.</li><li><b>Hip flexor:</b> half-kneel, tuck pelvis and shift gently forward.</li><li><b>Hamstring:</b> sit, one leg straight, hinge forward from the hips with a long back.</li><li><b>Glute (figure four):</b> on your back, ankle over the opposite knee, pull the legs toward you.</li><li><b>Quad:</b> standing, hold a wall, bring heel toward buttock, knees together.</li><li><b>Calf:</b> hands on a wall, back leg straight, heel down.</li><li><b>Spinal twist:</b> lying down, knees fall to one side, look the other way.</li></ol>
<h2>Desk or long-sitting break (3 minutes, every hour)</h2><ul><li>Stand up and march 30 seconds</li><li>10 shoulder rolls back</li><li>Chin tucks: slide chin straight back, 10 times</li><li>Standing back bend with hands on hips, 5 gentle times</li><li>10 calf raises</li><li>Look at something far away for 20 seconds</li></ul>
<h2>Mobility for joints</h2><p>Slow circles keep joints moving: ankles, knees (gently), hips, wrists, shoulders, 5 each way. Good first thing in the morning.</p>""")
P["yoga.html"] = ("Beginner yoga", f"""<h1>Beginner yoga</h1><p>Yoga here is simple stretching and balance practice with steady breathing. Use a towel or blanket on the floor. Move with the breath, never force a pose, and skip anything that hurts. Hold each pose for 3 to 5 slow breaths.</p>
<h2>Ten basic poses</h2>
<h3>1. Mountain</h3><p>Stand tall, feet hip width, weight even, arms by your sides, crown of the head lifting. The starting point for standing poses.</p>
<h3>2. Forward fold</h3><p>From standing, hinge at the hips and let your upper body hang. Bend your knees as much as you need. Roll up slowly.</p>
<h3>3. Downward-facing dog</h3>{F['dog']}<p>From hands and knees, tuck toes and lift hips up and back into an upside-down V. Knees can stay bent; heels do not need to touch the floor.</p>
<h3>4. Cat and cow</h3><p>On hands and knees, breathe in and let the belly drop with the gaze forward (cow); breathe out and round the back (cat).</p>
<h3>5. Child's pose</h3>{F['child']}<p>Kneel, sit back toward your heels, fold forward and rest your forehead on the floor or a cushion, arms forward or by your sides. A resting pose any time.</p>
<h3>6. Cobra</h3><p>Lie face down, hands under shoulders. Gently lift your chest using your back muscles, elbows bent and close in, shoulders down.</p>
<h3>7. Warrior II</h3><p>Step feet wide, turn the front foot out, bend the front knee over the ankle, arms out level with the floor, look over the front hand.</p>
<h3>8. Tree</h3>{F['tree']}<p>Stand on one leg, place the other foot on your ankle, calf or inner thigh (never on the knee). Hands at the chest or overhead. Hold a wall if needed.</p>
<h3>9. Bridge</h3><p>Same as the glute bridge: lie on your back, knees bent, lift your hips and breathe steadily.</p>
<h3>10. Resting pose</h3><p>Lie on your back, arms and legs relaxed, eyes closed, for 2 to 5 minutes. Let the breath be natural.</p>
<h2>Sun salutation (simple version)</h2><p>Move one step per breath. Repeat 3 to 5 rounds, slowly.</p><ol><li>Mountain, breathe in and raise arms overhead.</li><li>Breathe out, forward fold (knees bent if needed).</li><li>Breathe in, half lift: hands on shins, back flat.</li><li>Breathe out, step back to a plank, then lower knees, chest and chin (or lie down).</li><li>Breathe in, cobra.</li><li>Breathe out, downward dog; stay for 3 breaths.</li><li>Breathe in, step feet to hands, half lift.</li><li>Breathe out, forward fold.</li><li>Breathe in, roll up to stand with arms overhead; breathe out, hands down to mountain.</li></ol>
<div class="note">Pregnancy, high blood pressure, glaucoma, or neck and back problems: skip upside-down poses like downward dog and deep back bends unless a professional says they are fine.</div>""")
P["breathing.html"] = ("Breathing and meditation", """<h1>Breathing and meditation</h1><p>These are simple attention and breathing exercises. They can help with stress, focus and sleep. Sit or lie comfortably. If you feel dizzy, stop and breathe normally.</p>
<h2>Box breathing (2 to 4 minutes)</h2><ol><li>Breathe in through the nose for a count of 4.</li><li>Hold gently for 4.</li><li>Breathe out slowly for 4.</li><li>Hold for 4. Repeat.</li></ol><p>If holding is uncomfortable, use 3 counts or skip the holds.</p>
<h2>Slow calming breath</h2><p>Breathe in for 4, out for 6, about 6 breaths a minute, for 3 to 5 minutes. A longer out-breath tends to calm the body. Useful before sleep or after a scare.</p>
<h2>Body scan (5 to 10 minutes)</h2><ol><li>Lie down, close your eyes, notice the breath.</li><li>Bring attention to your toes; notice any sensation without changing it.</li><li>Slowly move up: feet, ankles, legs, hips, belly, chest, hands, arms, shoulders, neck, face.</li><li>If a part is tense, breathe out and let it soften.</li><li>Finish with a few breaths feeling the whole body.</li></ol>
<h2>Simple mindfulness (any time)</h2><ul><li><b>One-minute pause:</b> stop, take three slow breaths, notice what you can feel, hear and see.</li><li><b>5-4-3-2-1:</b> name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste. Helpful for anxiety or panic.</li><li><b>Mindful walk:</b> walk slowly, feeling each foot touch the ground.</li><li>When the mind wanders, that is normal: gently come back to the breath. That return is the practice.</li></ul>
<div class="note">If you have ongoing low mood, panic or trauma symptoms, these tools can help but are not a replacement for care. Talk to someone you trust or a health professional.</div>""")
P["plans.html"] = ("Sample weekly plans", """<h1>Sample weekly plans</h1><p>All plans need about 2 x 2 metres of floor and a sturdy chair. Always start with the 5-minute <a href="safety.html">warm-up</a> and finish with a few <a href="stretching.html">stretches</a>. Moves are on the <a href="calisthenics.html">bodyweight page</a>.</p>
<h2>Beginner (15 to 20 minutes, weeks 1 to 4)</h2><table><tr><th>Day</th><th>Session</th></tr>
<tr><td>Mon</td><td>Strength A: sit-to-stand 2x10, wall or counter push-up 2x10, glute bridge 2x12, plank 3x15 s</td></tr>
<tr><td>Tue</td><td>Brisk walk 15 to 20 min</td></tr><tr><td>Wed</td><td>Yoga: 3 sun salutations + tree, child's pose, resting pose</td></tr>
<tr><td>Thu</td><td>Strength B: split squat 2x6 each, knee push-up 2x6, step-ups 2x8 each, side plank 2x10 s each</td></tr>
<tr><td>Fri</td><td>Brisk walk 15 to 20 min</td></tr><tr><td>Sat</td><td>Stretching routine + box breathing 3 min</td></tr><tr><td>Sun</td><td>Rest or easy walk</td></tr></table>
<p>Each week add 2 reps or 5 seconds, or 5 minutes of walking. After 4 easy-feeling weeks, try intermediate.</p>
<h2>Intermediate (25 to 30 minutes)</h2><table><tr><th>Day</th><th>Session</th></tr>
<tr><td>Mon</td><td>Strength A: squat 3x15, push-up 3x10 to 15, single-leg bridge 3x8 each, plank 3x45 s</td></tr>
<tr><td>Tue</td><td>Intervals: 5 rounds of 20 s burpees / 40 s marching, then 15 min brisk walk</td></tr>
<tr><td>Wed</td><td>Yoga 20 min: 5 sun salutations, warrior II, tree, cobra, bridge, resting pose</td></tr>
<tr><td>Thu</td><td>Strength B: reverse lunge 3x10 each, chair dips 3x10, step-ups 3x12 each, side plank 3x30 s each</td></tr>
<tr><td>Fri</td><td>Circuit: 3 rounds of 10 squats, 10 push-ups, 10 lunges, 30 s plank, rest 1 min</td></tr>
<tr><td>Sat</td><td>Long walk 30 to 60 min + stretching</td></tr><tr><td>Sun</td><td>Rest, body scan</td></tr></table>
<h2>Short on time? (10 minutes)</h2><p>Warm-up 2 min, then 2 rounds: 10 squats, 8 push-ups (any level), 10 bridges, 20 s plank. Finish with 1 minute slow breathing.</p>""")
P["recovery.html"] = ("Recovery, sleep and water", """<h1>Recovery, sleep and water</h1>
<h2>Rest days</h2><p>Muscles get stronger between sessions. Leave at least one day between hard strength sessions for the same muscles. Light walking and stretching on rest days helps soreness.</p>
<h2>Soreness</h2><p>Stiffness 1 to 2 days after a new workout is normal and fades. Gentle movement helps more than complete rest. Very severe pain, swelling, or dark (cola-coloured) urine after hard exercise needs medical attention.</p>
<h2>Sleep</h2><ul><li>Adults need about 7 to 9 hours; teens 8 to 10.</li><li>Keep a regular wake time, even on weekends.</li><li>Get daylight in the morning; dim lights and screens in the last hour before bed.</li><li>Avoid caffeine late in the day and heavy meals right before sleep.</li><li>Cool, dark, quiet room. If you cannot sleep after about 20 minutes, get up and do something calm, then try again.</li></ul>
<h2>Water</h2><ul><li>Drink regularly through the day; pale yellow urine is a good sign.</li><li>Drink more in heat, at altitude, when sweating, or when ill.</li><li>For long sweaty sessions (over an hour), salt and sugar help: food plus water, or an oral rehydration drink.</li><li>Do not force huge amounts; too much water too fast can also be dangerous.</li></ul>
<h2>Food basics</h2><ul><li>Eat some protein at each meal (beans, lentils, eggs, fish, meat, dairy, nuts).</li><li>Plenty of vegetables, fruit and whole grains.</li><li>A small snack 1 to 2 hours before training if you are hungry.</li></ul>
<h2>Heat and cold</h2><p>In hot weather exercise early or late, go easier, and stop for headache, nausea, confusion or no longer sweating (heat illness). In cold, dress in layers and warm up longer.</p>""")
P["cheatsheet.html"] = ("Cheat sheet", """<div class="sheet"><h1>Fitness cheat sheet</h1>
<h2>Weekly target</h2><p>150 min moderate activity (brisk walk) + 2 strength sessions + a few minutes of stretching and balance most days.</p>
<h2>Every session</h2><p>Warm up 5 min (march, arm circles, hip circles, half squats) · work at "talk, not sing" · stop sets with 2 to 3 reps in reserve · stretch 5 min after.</p>
<h2>Stop now if</h2><p>Chest pain or pressure, unusual breathlessness, dizziness, racing or irregular heartbeat, sharp joint pain, numbness. Chest pain that does not stop with rest: get help.</p>
<h2>Moves</h2><table><tr><th>Move</th><th>Beginner</th><th>Intermediate</th></tr>
<tr><td>Push-up</td><td>Wall/counter/knee 2x8-12</td><td>Full 3x10-20</td></tr><tr><td>Squat</td><td>Sit-to-stand 2x10</td><td>Full 3x15-20</td></tr>
<tr><td>Lunge</td><td>Split squat 2x6 each</td><td>Reverse lunge 3x10 each</td></tr><tr><td>Glute bridge</td><td>2x12</td><td>Single-leg 3x8 each</td></tr>
<tr><td>Plank</td><td>Knees 3x15-20 s</td><td>3x30-60 s</td></tr><tr><td>Chair dip</td><td>Knees bent 2x6-8</td><td>Legs straight 3x10-15</td></tr>
<tr><td>Step-up</td><td>Low step 2x8 each</td><td>High step 3x12 each</td></tr><tr><td>Burpee</td><td>Step-back 2x5</td><td>3x8-12</td></tr></table>
<h2>Stretch (20 to 30 s, no bouncing)</h2><p>Neck · chest in doorway · cat-cow · hip flexor · hamstring · figure four · quad · calf · spinal twist.</p>
<h2>Yoga sun salutation</h2><p>Arms up · fold · half lift · plank, lower down · cobra · down dog 3 breaths · step forward, half lift · fold · rise, arms up · mountain.</p>
<h2>Breathing</h2><p>Box: in 4, hold 4, out 4, hold 4. Calm: in 4, out 6 for 3 to 5 min. Anxious: 5 see, 4 touch, 3 hear, 2 smell, 1 taste.</p>
<h2>Recover</h2><p>Sleep 7 to 9 h · pale yellow urine · protein each meal · rest day between hard sessions · light walking when sore.</p></div>""")
here = os.path.dirname(os.path.abspath(__file__)); out = os.path.join(here, "src")
nav = '<nav class="top">' + "".join(f'<a href="{h}">{t}</a>' for h, t in NAV) + "</nav>"
for name, (title, body) in P.items():
    open(os.path.join(out, name), "w").write(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Fitness Guide</title><link rel="stylesheet" href="style.css"></head><body><main>{nav}{body}{FOOT}</main></body></html>\n')
print(len(P), "pages")
