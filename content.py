"""Landing-page text and questionnaire definition (edit here, no code changes needed)."""
SECTIONS = [
 ("System Overload vs System Reboot", [("Overload", "Too much screen time, stress and low energy."), ("Reboot", "Focus, strength and resilience through regular movement.")]),
 ("Brain Fitness: The BDNF Cycle", [("1", "Movement"), ("2", "Blood Flow"), ("3", "BDNF Release"), ("4", "Neurogenesis"), ("5", "Cognitive Superpower")]),
 ("Growth Mechanics", [("Progressive overload", "Do a little more over time."), ("Periodization", "Adaptation (weeks 1-2), Transformation (weeks 3-4)."), ("Recovery", "Rest and sleep make you stronger."), ("Golden Rule", "5-minute warm-up and 5-minute cool-down in every session.")]),
 ("The 6 Pillars of Balance", [(p, "") for p in ["Aerobic", "Strength", "Flexibility", "Balance & Coordination", "Outdoor", "Team Sports"]]),
 ("10 Rules for Vitality", [("Plate matrix", "Half vegetables/fruit, a quarter protein, a quarter whole grains."), ("Hydration", "Sip water all day."), ("Smart fuel", "Real food, no strict diets."), ("Biorhythms", "Regular sleep and wake times."), ("System routine", "A simple daily routine."), ("4-7-8 breathing", "Inhale 4, hold 7, exhale 8."), ("Digital detox", "Screen-free hour before bed."), ("Dopamine defense", "Phone away while you move."), ("Habit tracking", "Tick every active day."), ("Micro-celebrations", "Celebrate small wins.")]),
 ("Expectation vs Reality", [("I have no time", "3 x 10-minute movement snacks."), ("I'm afraid of injury", "The Warm-Up Law: 5 min before, 5 min after."), ("Training alone is boring", "Find a fitness buddy.")]),
 ("The Winning Mindset", [("Week two", "Expect a dip. Keep sessions small. Never miss two days in a row."), ("Weekly Challenge", "Close the Rings: sessions, steps and recovery habits.")]),
 ("The Team", [("Rashidov Iskandar", ""), ("Xidirov G'olibjon", ""), ("Tohirov Iskandar", ""), ("Shermamatov Zafarbek", "")]),
]
# (section title, [(field, label, type, options)])  type: sel | multi | num
QUESTIONS = [
 ("Basics", [("gender", "Gender (optional)", "sel", ["Female", "Male", "Other", "Skip"]), ("h", "Height (cm)", "num", []), ("w", "Weight (kg)", "num", [])]),
 ("Fitness level", [("walk", "Can you walk 30 minutes without stopping?", "sel", ["Yes", "With rests", "Not yet"]), ("jog", "Can you jog 10 minutes?", "sel", ["Yes", "Almost", "No"]), ("act", "Active days per week now", "sel", ["0", "1-2", "3-4", "5+"])]),
 ("Safety", [("lim", "Any limits?", "multi", ["Knee", "Back", "Shoulder", "Balance/mobility aid", "Returning from injury", "Pregnancy/postpartum", "None"]), ("fear", "Afraid of injury?", "sel", ["Yes", "A bit", "No"])]),
 ("Lifestyle", [("free", "Free time per day (minutes)", "sel", ["10", "20", "30", "45"]), ("stress", "Stress level (1-5)", "sel", ["1", "2", "3", "4", "5"]), ("sleep", "Sleep hours", "sel", ["<6", "6-7", "8+"])]),
 ("Preferences", [("eq", "Equipment", "multi", ["None", "Bands", "Dumbbells", "Bike", "Gym", "Pool"]), ("fav", "Favourite activities", "multi", ["Walking", "Jogging", "Yoga", "Swimming", "Cycling", "Hiking", "Football", "Basketball", "Dance", "Pilates"]), ("soc", "Train with", "sel", ["Solo", "Friends/family"])]),
 ("Main goal", [("goal", "What matters most?", "sel", ["More energy", "Better focus", "Stronger body", "Less stress", "Better posture", "Healthy ageing", "More confidence"])]),
]
