"""Rule-based 4-week plan generator. No calories, weight targets or diets (safe for under 18s)."""
from datetime import date

# (type, activity, minutes) - Phase 01 Adaptation (weeks 1-2) and Phase 02 Transformation (weeks 3-4)
P1 = [("Aerobic", "Light jog / brisk walk", 20), ("Flexibility & Balance", "Yoga / stretching", 15),
      ("Strength base", "Bodyweight circuit", 20), ("Active recovery", "Brisk walk", 30),
      ("Team / fun", "Sport or fun activity", 40), ("Outdoor", "Cycling / hiking", 45), ("Rest", "Full rest day", 0)]
P2 = [("Aerobic", "Interval cardio", 30), ("Flexibility & Balance", "Advanced yoga flow", 25),
      ("Strength", "Resistance bands + extra sets", 30), ("Active recovery", "Recovery walk", 30),
      ("Team / fun", "High-intensity or match play", 50), ("Outdoor", "Distance cycling / hiking", 60), ("Rest", "Full rest day", 0)]
KID = ["Tag & running games", "Animal-walk yoga", "Obstacle course", "Family walk", "Team game", "Park adventure"]
SENIOR = ["Brisk walk or marching", "Chair yoga / tai chi", "Chair-stand & band circuit", "Gentle walk",
          "Water aerobics / social walk", "Easy outdoor stroll"]
EX = {"Aerobic": ["Walk/jog at an easy pace (talk test)", "Every 5 min: 30 s faster", "Finish easy"],
      "Flexibility & Balance": ["Cat-cow 2x8", "Hamstring stretch 2x30 s each", "Single-leg stand 3x20 s (hold a chair)"],
      "Strength base": ["Squat or chair-stand 2x10", "Wall/knee push-up 2x8", "Plank 2x20 s", "Glute bridge 2x10"],
      "Strength": ["Squat 3x12", "Push-up 3x8", "Band row 3x12", "Plank 3x30 s"],
      "Active recovery": ["Easy steady walk", "Relax shoulders, breathe slowly"],
      "Team / fun": ["Play at a fun pace", "Rest and sip water often"], "Outdoor": ["Steady pace", "Rest break every 15 min"]}
KID_EX = {"Aerobic": ["Tag, 5 rounds", "Frog jumps 3x10"], "Flexibility & Balance": ["Animal poses 6x20 s", "One-foot balance 3x10 s"],
          "Strength base": ["Bear crawl 3x10 steps", "Jumping jacks 3x10"], "Strength": ["Obstacle course, 4 laps"]}
TIPS = ["Plate matrix: build meals with vegetables, protein and whole grains.", "Drink water regularly; carry a bottle.",
        "Keep regular sleep times; digital detox 1 hour before bed.", "Practise 4-7-8 breathing for 2 minutes each evening."]


def age_of(dob: str) -> int:
    d, t = date.fromisoformat(dob), date.today()
    return t.year - d.year - ((t.month, t.day) < (d.month, d.day))


def group(age: int) -> str:
    return "kid" if age < 13 else "teen" if age < 18 else "adult" if age < 60 else "senior"


def steps_goal(age: int, act: str) -> int:
    base = 6000 if age < 13 or age >= 60 else 10000
    return int(base * (0.6 if act == "0" else 1))


def r5(x: float) -> int:
    return int(x / 5 + 0.5) * 5


def gen_plan(a: dict, age: int) -> list:
    g = group(age)
    beginner = a.get("walk") != "Yes" or a.get("act") == "0"
    advanced = a.get("act") == "5+" and a.get("jog") == "Yes"
    mult = 0.75 if beginner else 1.25 if advanced else 1.0
    lim, eq = a.get("lim", []), a.get("eq", [])
    fav = [f for f in a.get("fav", []) if f != "Walking"]
    free = int(a.get("free") or 30)
    weeks = []
    for w in range(4):
        days = []
        for i, (ty, name, mins) in enumerate(P1 if w < 2 else P2):
            notes = []
            if g == "kid":
                name = KID[i] if i < 6 else name
                mins = min(60, max(30, mins)) if mins else 0
            elif g == "senior" and i < 6:
                name, mins = SENIOR[i], r5(mins * 0.7)
            else:
                mins = r5(mins * mult)
            if i == 4 and fav and g != "kid":                      # preferences replace the fun day
                name = fav[w % len(fav)] + " session"
            if g == "adult" and i == 2 and ("Dumbbells" in eq or "Gym" in eq):
                name += " + dumbbells"
            if ("Knee" in lim or "Back" in lim) and i == 0:        # limitations -> low-impact swap
                name = "Cycling, swimming or easy walk"; notes.append("Low-impact swap for your limits.")
            if "Shoulder" in lim and i == 2:
                notes.append("Skip push-ups; use band rows and bridges.")
            goal = a.get("goal")                                    # goal emphasis on Thursday
            if i == 3:
                if goal == "Better focus": name, ty = "Aerobic walk-jog", "Aerobic"
                elif goal == "Stronger body": name, ty = "Bodyweight strength", "Strength base"
                elif goal == "Less stress": name = "Walk + 4-7-8 breathing"
                elif goal == "Better posture": name = "Mobility & core"
                elif goal == "Healthy ageing": name, ty = "Balance & mobility", "Flexibility & Balance"
            if a.get("soc") == "Solo" and i == 4:
                notes.append("Solo option: do it alone or invite a buddy.")
            if g == "senior" and mins:
                notes.append("Sitting alternative for every exercise; longer rests are fine. Check with your doctor first.")
            if g == "kid" and mins:
                notes.append("Parent joins in. 30-60 min total movement per day, no heavy resistance.")
            ex = (KID_EX.get(ty) if g == "kid" else None) or EX.get(ty, [])
            days.append({"ty": ty, "nm": name, "mn": mins, "ex": ex, "nt": notes, "snack": free <= 20 and mins > 0})
        weeks.append({"tips": TIPS[w], "days": days})
    return weeks


def scale_plan(plan: list, from_week: int, factor: float) -> list:
    """'Too hard' (0.85) / 'Too easy' (1.15) adjusts this week and later ones."""
    for wi, wk in enumerate(plan):
        if wi >= from_week:
            for d in wk["days"]:
                if d["mn"]:
                    d["mn"] = max(10, r5(d["mn"] * factor))
    return plan


def streak(done: set) -> int:
    """Never miss two days in a row: gaps of up to one day keep the streak alive."""
    idx = sorted((w * 7 + d for w, d in done), reverse=True)
    s, prev = 0, None
    for x in idx:
        if prev is None or prev - x <= 2:
            s += 1; prev = x
        else:
            break
    return s
