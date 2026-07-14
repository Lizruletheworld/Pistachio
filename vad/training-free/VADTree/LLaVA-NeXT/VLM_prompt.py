# vera_q = '''You are the model.Model Description: You are designed to do binaryclassification. The input is a sequence of video frames foridentifying whether there is an anomaly in the video; youneed to output the class label, i.e., an integer in the set {0,1}. 0 represents normal video, and 1 represents abnormalvideo. Please answer the prompt questions.Prompt Questions: Answer the following questions basedon what you see from the video frames and provide anexplanation in one sentence.1. Are there any people in the video who arenot in their typical positions or engaging inactivities that are not consistent with theirusual behavior?2. Are there any vehicles in the video that arenot in their typical positions or being usedin a way that is not consistent with theirusual function?3. Are there any objects in the video that arenot in their typical positions or being usedin a way that is not consistent with theirusual function?4. Is there any visible damage or unusualmovement in the video that indicates ananomaly?5. Are there any unusual sounds or noisesin the video that suggest an anomaly? Based on the analysis above, please conclude your answerto "Is there any anomaly in the video?" in "Yes, there is ananomaly" or "No, there is no anomaly".Please give your output strictly in the following format:• Answers to Prompt Questions: [Provide your analysisby answering the questions listed in Prompt Questions.]• Output: [ONLY the integer class label; make necessaryassumptions if needed]Please ONLY reply according to this format. Don't giveme any other words.'''
"""
ucf gen_prior:
To help video anomaly detection agent review the occurrence of abnormal events, it is now necessary to pre-analyze
possible anomalies to establish a prior knowledge base that matches abnormal events. The video taken has no sound, and may have a long distance or a blurry picture. There may be Abuse,Arrest,Arson, Assault, Burglary, Explosion, Fighting, RoadAccidents, Robbery, Shooting，Shoplifting, Stealing, Vandalism 13 types of events. Please carefully analyze these sences.Then point out the characteristics of each abnormal event from the following three perspectives: the scene environment, characters or specific objects, actions or behaviors that occurred.
pistachio_gen_prior:
To help video anomaly detection agent review the occurrence of abnormal events, ...
There may be Animal Abuse, Animal Attack or Fight, ..., Wild Large Animal Intrusion 31 types of events.
Please carefully analyze these scenes. Then point out the characteristics of each abnormal event from the
following three perspectives: the scene environment, characters or specific objects, actions or behaviors
that occurred.
xd gen_prior:
To help video anomaly detection agent review the occurrence of abnormal events, it is now necessary to pre-analyze possible anomalies to establish a prior knowledge base that matches abnormal events. The video taken has no sound, and may have a long distance or a blurry picture. There may be Abuse,  Explosion, Fighting, Car Accident, Shooting, Roit 6 types of events. Please carefully analyze these sences.Then point out the characteristics of each abnormal event from the following three perspectives: the scene environment, characters or specific objects, actions or behaviors that occurred.

msad gen_prior:
To help video anomaly detection agent review the occurrence of abnormal events, it is now necessary to pre-analyze
possible anomalies to establish a prior knowledge base that matches abnormal events. The video taken has no sound, and may have a long distance or a blurry picture. There may be Assault, Explosion, Fighting, Fire, Object Falling, People Falling, Robbery,  Shooting, Traffic Accidents, Vandalism, Water Incident 11 types of events. Please carefully analyze these sences.Then point out the characteristics of each abnormal event from the following three perspectives: the scene environment, characters or specific objects, actions or behaviors that occurred.
"""
msad_prior_q = '''Below is a detailed analysis of each abnormal event type from scene environment, characters/specific objects, and actions/behaviors perspectives. The analysis accounts for video limitations (no sound, long distance, blurriness) and focuses on visually detectable anomalies.

1. Assault

• Scene Environment:

  Dark or isolated areas (alleys, parking lots), public spaces with limited visibility (park corners, subway stations).
• Characters/Specific Objects:

  Two key individuals: aggressor (tense posture, clenched fists) and victim (defensive stance, recoiling). Weapons may appear as metallic blurs (knives, bats).
• Actions/Behaviors:

  Aggressor lunging toward victim, swinging arms violently. Victim staggering backward, shielding face, or collapsing. Rapid, erratic movements distinguish it from casual interaction.

2. Explosion

• Scene Environment:

  Open public areas (markets, streets) or enclosed spaces (buildings, vehicles). Sudden bright flash against surroundings.
• Characters/Specific Objects:

  Smoke/fireball expanding rapidly, flying debris (indistinct chunks). People thrown backward; panic-induced crowd chaos.
• Actions/Behaviors:

  Blast wave propelling objects/bodies horizontally. Secondary fires igniting. Crowds scattering chaotically or collapsing.

3. Fighting

• Scene Environment:

  Crowded venues (bars, stadiums) or public zones (streets, parks). Disrupted scenery (overturned tables, broken items).
• Characters/Specific Objects:

  2+ combatants in aggressive stances. Objects used as weapons (chairs, bottles). Bystanders recoiling.
• Actions/Behaviors:

  Mutual swinging/punching/kicking. Tussling on ground, grappling. Bystanders fleeing or attempting intervention.

4. Fire

• Scene Environment:

  Buildings (windows emitting smoke), forests, or vehicles. Intense orange glow in low-light settings.
• Characters/Specific Objects:

  Flames/smoke plumes (distinct against backdrop). Panicked crowds, firefighters (identifiable uniforms/hoses).
• Actions/Behaviors:

  Rapid fire spread across structures/trees. People fleeing with hands covering faces. Collapsing structures/exploding objects.

5. Object Falling

• Scene Environment:

  Construction sites, high-rise areas, warehouses. Suspended objects (cranes, shelves) before fall.
• Characters/Specific Objects:

  Falling objects (debris, equipment). Workers/crowds below reacting. Scaffolding/structures unstable.
• Actions/Behaviors:

  Sudden vertical descent of heavy objects. People dodging or struck. Secondary impacts (dust clouds, structural collapse).

6. People Falling

• Scene Environment:

  Heights (balconies, cliffs), staircases, elevated platforms. Lack of safety rails.
• Characters/Specific Objects:

  Person mid-fall (unnatural posture). Others attempting to grab them. Ground/obstacles below (e.g., concrete, water).
• Actions/Behaviors:

  Slipping/tripping, followed by uncontrolled descent. Sudden impact with ground, often leaving body motionless. Crowds rushing to aid.

7. Robbery

• Scene Environment:

  Retail stores, banks, ATMs, or streets. Cash registers/vaults as focal points.
• Characters/Specific Objects:

  Robber (masked/covered face, weapon blur). Victim handing over items. Stolen goods (bags, cash).
• Actions/Behaviors:

  Weapon brandishing (gun-shaped object). Aggressive grabbing of valuables. Perpetrator fleeing; victims cowering or chasing.

8. Shooting

• Scene Environment:

  Crowded spaces (malls, streets), indoor venues. Minimal cover for victims.
• Characters/Specific Objects:

  Shooter aiming firearm (elongated object in hand). Victims collapsing, blood splatters (dark blobs).
• Actions/Behaviors:

  Shooter’s recoil motion, muzzle flashes. People diving for cover or fleeing. Chaotic crowd dispersion from gunfire origin.

9. Traffic Accidents

• Scene Environment:

  Roads, intersections, highways. Skid marks, damaged barriers.
• Characters/Specific Objects:

  Colliding vehicles (deformed shapes, deployed airbags). Injured pedestrians/cyclists. Shattered glass/debris.
• Actions/Behaviors:

  Sudden vehicle swerving, impact with crunching metal. Bodies flung over hoods. People exiting cars in shock.

10. Vandalism

• Scene Environment:

  Public property (walls, buses), abandoned buildings. Fresh paint/graffiti or shattered surfaces.
• Characters/Specific Objects:

  Perpetrator (spray cans, rocks). Damaged property (broken windows, defaced walls).
• Actions/Behaviors:

  Spraying walls, smashing glass with blunt objects. Quick escape after destruction. Onlookers pointing/shouting.

11. Water Incident

• Scene Environment:

  Water bodies (pools, rivers, beaches), flooded streets. Waves/swirls in water.
• Characters/Specific Objects:

  Person submerged/flailing in water. Bystanders on shore. Rescue gear (life rings, boats).
• Actions/Behaviors:

  Sudden submersion or drowning motions (arms thrashing). Failed attempts to swim. Rescuers diving in or throwing ropes.

Key Cross-Cutting Observations

• Panic Signifiers: Crowd scattering in all directions, limb flailing, or collapsing.

• Motion Clues: Sudden acceleration (explosions, falls), unnatural trajectories (object/person falling), violent limb movements (fights).

• Blur/Distance Adaptation:

  • Focus on contrast (fire/smoke vs. background, flash vs. dark).

  • Detect shape deformities (e.g., vehicles post-crash, slumped bodies).

  • Track crowd motion anomalies (e.g., chaos in explosions vs. directional fleeing in shootings).
'''

xd_prior_q = '''To establish a prior knowledge base for detecting the six abnormal events in low-quality, silent video footage, the following characteristics are prioritized based on observable visual cues, even from a distance or in blurry conditions:

---

**1. Abuse**
• Scene Environment:

  • Secluded or private settings (e.g., alleyways, dimly lit rooms, isolated corners).

  • Lack of bystanders or confined spaces.

• Characters/Specific Objects:

  • Two or more individuals, with one appearing dominant (larger posture) and the other submissive (cowering, retreating).

  • Objects like belts, sticks, or household items may be present but might be indistinct.

• Actions/Behaviors:

  • Sudden aggressive movements (e.g., hitting, grabbing, shoving).

  • Victim recoiling, shielding themselves, or attempting to flee.

  • Prolonged physical contact in a confrontational posture.


---

**2. Explosion**
• Scene Environment:

  • Sudden bright flash followed by smoke/fire, even in blurry footage.

  • Debris flying outward or structural damage (e.g., collapsed walls, shattered windows).

• Characters/Specific Objects:

  • People running chaotically or thrown off balance.

  • Vehicles, trash bins, or other objects near the blast source.

• Actions/Behaviors:

  • Rapid expansion of light/smoke from a focal point.

  • Crowds scattering in all directions post-explosion.

  • Lingering smoke or flames after the initial flash.


---

**3. Fighting**
• Scene Environment:

  • Public areas (streets, parks, bars) with bystanders forming a circle around the altercation.

• Characters/Specific Objects:

  • Two or more individuals in close proximity with aggressive postures.

  • Broken objects (e.g., bottles, chairs) nearby.

• Actions/Behaviors:

  • Repetitive punching, kicking, or grappling.

  • Erratic, high-intensity movements with sudden direction changes.

  • Bystanders fleeing or attempting to intervene.


---

**4. Car Accident**
• Scene Environment:

  • Roads, intersections, or highways with sudden traffic stoppages.

  • Skid marks, scattered debris (e.g., broken glass, car parts).

• Characters/Specific Objects:

  • Collided vehicles (distorted shapes, misaligned positions).

  • Injured individuals or people exiting vehicles abruptly.

• Actions/Behaviors:

  • Rapid deceleration or collision impact (sudden stop/change in motion).

  • Post-crash behaviors: drivers inspecting damage, crowds gathering, emergency services arriving.


---

**5. Shooting**
• Scene Environment:

  • Public spaces (malls, streets) with crowds reacting suddenly.

  • Visible escape routes (people running toward exits).

• Characters/Specific Objects:

  • Shooter’s stance: arm extended, recoil motion (even if the gun is blurry).

  • Victims collapsing, clutching limbs/torso, or hiding behind cover.

• Actions/Behaviors:

  • Crowd panic: people ducking, sprinting, or taking cover.

  • Distinctive post-shooting patterns (e.g., bodies on the ground, law enforcement rushing in).


---

**6. Riot**
• Scene Environment:

  • Large crowds in streets or public squares, often with fires or smoke.

  • Broken infrastructure (smashed windows, overturned vehicles).

• Characters/Specific Objects:

  • Protesters with makeshift weapons (sticks, rocks).

  • Law enforcement in riot gear or armored vehicles.

• Actions/Behaviors:

  • Group violence: throwing objects, setting fires, clashing with police.

  • Wave-like crowd movements, chaotic dispersal patterns.


---

Key Considerations for Low-Quality Footage:
• Focus on movement patterns (e.g., sudden scattering, aggressive postures).

• Detect environmental changes (smoke, fire, debris) over fine details.

• Use group dynamics (crowd panic, clustering) as indirect indicators.

• Prioritize spatial-temporal anomalies (e.g., rapid light flashes, abnormal vehicle stops).


These features allow the agent to infer anomalies without relying on audio or high-resolution details.
'''

ucf_prior_q = '''Here is a consolidated table of **14 types of abnormal events**, analyzed comprehensively from three
perspectives: **scene environment, characters/objects, and actions/behaviors** (adapted for silent, long-distance, or blurry video scenarios):

---

| **Abnormal Event Type**      | **Scene Environment Features**                                                                 | **Character/Object Features**                                                          | **Action/Behavior Features**                                                           |
|-------------------------------|-------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| **Abuse**                     | Secluded spaces (indoors/corners), non-public areas (private locations)                        | Two parties in physical conflict (perpetrator/victim), dragging tools (ropes/clubs)   | Shoving/dragging, repeated hitting, restraining movement (pinning down)               |
| **Arrest**                    | Public areas (streets/squares), zones with police vehicles or officers                         | Uniformed police, handcuffs, batons or firearms                                        | Forced restraint, frisking, escorting to vehicles, lying on the ground                |
| **Arson**                     | Areas with flammable materials (warehouses/vehicles), abnormal smoke/flames                     | Individuals holding flammable containers (gasoline bottles), ignition tools (lighters) | Throwing incendiary objects, fleeing quickly, repeatedly checking the fire            |
| **Assault**                   | Narrow passages, crowded areas with sudden dispersion (subway stations/bar entrances)          | Armed individuals (knives/blunt weapons), victims struggling on the ground           | Sudden lunging, weapon swinging, victims adopting defensive postures                  |
| **Burglary**                  | Damaged doors/windows, unlit buildings at night, surveillance blind spots (back alleys)        | Masked/dark-clothed individuals, lock-picking tools (pliers), backpacks (for loot)    | Peering through windows, picking locks, rummaging through items                       |
| **Explosion**                 | Smoke spreading, flying debris, crowds fleeing outward from a central point                    | Suspicious packages/vehicles, post-explosion wreckage (metal fragments)             | Throwing motions, sudden flash of flames, crowds crouching/running                   |
| **Fighting**                  | Public spaces (restaurants/stadiums) with concentrated physical conflicts,
overturned furniture| Multiple people entangled, bleeding faces, torn clothing                              | Punching/kicking, hair-pulling, siege                                             |
| **Road Accidents**            | Collision points (intersections/curves), skid marks, scattered debris, traffic congestion      | Deformed vehicles, deployed airbags, paramedics (uniforms/stretchers)                 | Sudden braking, vehicle rollovers, pedestrians being hit                              |
| **Robbery**                   | Streets/ATM areas, fast-moving vehicles (motorcycles/cars)                                      | Threats with guns/knives, motorcycle helmets (face concealment), stolen items (bags)  | Snatching and fleeing, threatening gestures, vehicles abruptly stopping/accelerating |
| **Shooting**                  | Crowds suddenly ducking/fleeing, vehicles braking abruptly, bullet holes in windows             | Gun-wielding individuals, gunshot victims falling, spent shell casings                | Aiming firearms, continuous firing, seeking cover                                    |
| **Shoplifting**               | Loitering near shelves, surveillance blind spots (corners), suspicious concealment (coats)      | Frequently observing staff, hiding items (in bags/under clothing)                    | Concealing items in clothing, glancing around nervously, quickly leaving shelves       |
| **Stealing**                  | Crowded areas (subways/markets), sudden disappearance of target items (wallets/phones)          | Close proximity to victims, distractions (e.g., bumping), rapid transfer of stolen goods | Pickpocketing (hands reaching into pockets), passing loot to accomplices              |
| **Vandalism**                 | Graffiti-covered walls, shattered glass, toppled public facilities (trash cans/fences)          | Spray paint cans, hammers/stones, targets (cameras/glass)                            | Smashing motions, spraying walls, kicking facilities                                 |

---

### **Table Notes**
1. **Scene Environment**: Highlights spatial anomalies (e.g., secluded corners, fleeing crowds) and physical damage (broken doors, smoke/flames).
2. **Characters/Objects**: Focuses on suspicious individuals (masked/armed) or high-risk objects (weapons/flammables).
3. **Actions/Behaviors**: Describes intense or abnorma actions (weapon swinging, rapid fleeing), critical for
low-quality
video analysis.

### **Tips for Low-Quality Video Recognition**
• **Blurry Footage**: Prioritize **group behavior sudden change** (e.g., fleeing crowds) and **object trajectories** (explosion
debris).
• **Long-Distance Scenes**: Rely on **environmental damage dynamics** (shattering glass, spreading smoke) and **large-scale conflicts** (fights/robberies).
• **Silent Videos**: Infer anomalies via **action intensity** (repeated hitting, vehicle rollovers) and **object interactions** (throwing incendiaries, lock-picking).

This consolidated table serves as a prior knowledge base for video anomaly detection systems, improving accuracy through multi-dimensional feature combinations.
'''

ucf_short_prior_q='''
This table summarizes key features of 14 abnormal events from three perspectives for video analysis.

| Event Type | Scene Environment | Characters/Objects | Actions/Behaviors |
| :--- | :--- | :--- | :--- |
| **Abuse** | Secluded, non-public areas | Two parties in conflict, tools | Shoving, repeated hitting, restraining |
| **Arrest** | Public areas, police presence | Uniformed police, handcuffs | Restraint, frisking, escorting |
| **Arson** | Flammable materials, smoke/flames | Flammable containers, lighters | Throwing objects, fleeing |
| **Assault** | Crowded areas with dispersion | Armed individuals, victims | Lunging, weapon swinging, defending |
| **Burglary** | Damaged entry points, unlit | Masked individuals, tools | Peering, picking locks, rummaging |
| **Explosion** | Smoke/debris, fleeing crowds | Suspicious packages, wreckage | Throwing motion, flash, fleeing |
| **Fighting** | Public spaces, overturned items | Multiple entangled people | Punching/kicking, brawling |
| **Road Accidents** | Collision points, debris | Deformed vehicles, paramedics | Sudden braking, rollovers, impacts |
| **Robbery** | Streets/ATMs, fast vehicles | Weapons, concealed faces, loot | Snatching, threatening, fleeing |
| **Shooting** | Ducking/fleeing crowds, bullet holes | Gun-wielding individuals, victims | Aiming, firing, seeking cover |
| **Shoplifting** | Store shelves, blind spots | Observing staff, hiding items | Concealing, glancing nervously |
| **Stealing** | Crowded areas | Close proximity, distractions | Pickpocketing, transferring goods |
| **Vandalism** | Graffiti, broken glass/facilities | Spray cans, tools | Smashing, spraying, kicking |

**Key Analysis Framework:**
*   **Scene:** Spatial anomalies and physical damage.
*   **Characters/Objects:** Suspicious individuals and high-risk items.
*   **Actions/Behaviors:** Intense, rapid, or anomalous movements.

**Tips for Low-Quality Video:**
*   **Blurry:** Focus on group behavior changes and object trajectories.
*   **Long-Distance:** Rely on environmental dynamics and large-scale motion.
*   **Silent:** Infer from action intensity and object interactions.
'''
# prompt_flag = '_prior_q'

q = 'Please describe in one sentence what happened in the video.'
# q0 = 'You are an AI assistant for understanding video anomaly events. Please carefully analyze the video ' \
#      'from the three perspectives of Scene Environment, Characters/Objects, Actions/Behaviors based on the ' \
#      'above prior information, and then give the description of the video.'
# prompt_flag = '_question'

q1 = 'You are an AI assistant for understanding video anomaly events. The video is silent and the picture quality may be poor. The video may contain 13 dangerous, violent or criminal events: Abuse, Arrest, Arson, Assault, Burglary, Explosion, Fighting, RoadAccidents, Robbery, Shooting, Shoplifting, Stealing, Vandalism. Please follow the following four steps to understand and analyze the video. 1. Understand the scene environment; 2. Understand the identity of the characters and the objects that appear; 3. Understand the actions and behaviors of the characters and the movement of the objects; 4. Based on the understanding of the above three aspects, give a detailed description of the video content.'
# prompt_flag = '_q1'

q2 = 'Please describe the video content in detail from three perspectives: the shooting environment, the people and objects that appear, and the movements and behaviors that occur. Do not include other irrelevant text.'
q3 = 'Please describe the video content in detail from three perspectives: the location and time, the people and objects that appear, and the movements and behaviors that occur. Do not include other irrelevant text.'

q5 = 'Please describe the content in the video in detail.'

sq = 'Please describe in one sentence what happened in the video.'

draw_mask = 'The areas marked with red outlines in some frames are areas of obvious motion. '

ucf_prior_q = ucf_prior_q + '\n' + q5
xd_prior_q = xd_prior_q + '\n' + q5
msad_prior_q = msad_prior_q + '\n' + q5

ucf_prior_sq = ucf_prior_q + '\n' + sq
xd_prior_sq = xd_prior_q + '\n' + sq
msad_prior_sq = msad_prior_q + '\n' + sq

ucf_prior_dq = ucf_prior_q + '\n' + draw_mask + q5
xd_prior_dq = xd_prior_q + '\n' + draw_mask + q5
msad_prior_dq = msad_prior_q + '\n' + draw_mask + q5
pistachio_prior_q = '''Below is a detailed analysis of each abnormal event type from scene environment, characters/specific objects, and actions/behaviors perspectives. The analysis accounts for video limitations (no sound, long distance, blurriness) and focuses on visually detectable anomalies.

1. Animal Abuse
- Scene Environment:
  Secluded areas (backyards, rural roads), farms, or alleys with few bystanders.
- Characters/Specific Objects:
  One or more humans and an animal (dog, cat, livestock). Objects like ropes, sticks, or cages may be present.
- Actions/Behaviors:
  Human striking, kicking, or restraining animal in unnatural posture. Animal cowering, writhing, or attempting to flee. Sudden violent contact between human and animal.

2. Animal Attack or Fight
- Scene Environment:
  Open outdoor areas (fields, forests, parks, zoo enclosures), or rural settings.
- Characters/Specific Objects:
  One or more animals in aggressive posture. Human victim nearby (fleeing or on ground). Blood stains or scattered objects.
- Actions/Behaviors:
  Animal charging or lunging at human/other animal. Victim falling or running chaotically. Rapid biting/clawing motions.

3. Animal Fall and Injury
- Scene Environment:
  Construction sites, cliffs, farm structures, or elevated terrain.
- Characters/Specific Objects:
  Animal mid-fall or motionless on ground. Humans rushing toward the animal.
- Actions/Behaviors:
  Sudden uncontrolled descent of animal. Impact with ground leaving animal stationary. Bystanders gathering or panicking.

4. Animal Fight
- Scene Environment:
  Open fields, enclosures, streets, or rural areas with minimal human presence.
- Characters/Specific Objects:
  Two or more animals in physical contact (dogs, bulls, wildlife).
- Actions/Behaviors:
  Biting, wrestling, charging between animals. Dust/debris raised by violent movement. Onlookers fleeing or retreating.

5. Animal Predation
- Scene Environment:
  Wildlife habitats (savanna, forest, grassland) or farm/rural environments.
- Characters/Specific Objects:
  Predator animal pursuing prey. Prey animal in flight or subdued on ground.
- Actions/Behaviors:
  High-speed chase, pouncing, or sustained pinning of prey. Prey struggling or going limp. Predator crouching or feeding.

6. Avalanche
- Scene Environment:
  Mountain slopes with snow cover. Sudden large-scale movement of white mass downhill.
- Characters/Specific Objects:
  Rapidly descending snow/debris cloud. Skiers, hikers, or vehicles in its path.
- Actions/Behaviors:
  Massive snow front accelerating downslope. People or objects engulfed or swept aside. Cloud of snow dust expanding.

7. Construction Accident
- Scene Environment:
  Active construction sites with scaffolding, cranes, heavy machinery, or excavations.
- Characters/Specific Objects:
  Workers in helmets/vests, falling debris, collapsing structures, heavy equipment.
- Actions/Behaviors:
  Sudden collapse of scaffold or material. Worker falling or struck by object. Machinery tipping or malfunctioning violently.

8. Equipment Breakdown
- Scene Environment:
  Industrial facilities, factories, construction sites, or roads with heavy machinery.
- Characters/Specific Objects:
  Malfunctioning machinery (sparks, smoke, visible structural failure). Workers reacting suddenly.
- Actions/Behaviors:
  Machine halting abruptly or emitting smoke/sparks. Workers backing away or running. Visible mechanical deformation or collapse.

9. Explosion
- Scene Environment:
  Open public areas, industrial zones, vehicles, or buildings. Sudden bright flash.
- Characters/Specific Objects:
  Smoke/fireball expanding rapidly, flying debris. People thrown backward or fleeing.
- Actions/Behaviors:
  Blast wave propelling objects/bodies. Secondary fires igniting. Crowds scattering chaotically or collapsing.

10. Extreme Weather Events
- Scene Environment:
  Outdoor environments during storms (flooded streets, falling trees, high winds, hail).
- Characters/Specific Objects:
  Bent trees, flying debris, flooded roads, vehicles submerged or overturned.
- Actions/Behaviors:
  Objects blown or swept away. People struggling to walk or sheltering in place. Sudden inundation or structural damage from wind/water.

11. Falling Object and Collapse
- Scene Environment:
  Construction zones, high-rise buildings, shelving areas, or cliff faces.
- Characters/Specific Objects:
  Falling debris, collapsed structures, workers/pedestrians below.
- Actions/Behaviors:
  Sudden downward trajectory of heavy objects. People dodging or being struck. Dust cloud from impact; secondary collapse.

12. Fighting and Physical Conflict
- Scene Environment:
  Public spaces (streets, bars, stadiums) with disrupted surroundings (overturned objects).
- Characters/Specific Objects:
  2+ people in aggressive postures. Broken objects nearby. Bystanders recoiling.
- Actions/Behaviors:
  Mutual punching/kicking/grappling. Bodies falling or tussling on ground. Crowd forming or fleeing.

13. Fire
- Scene Environment:
  Buildings, forests, vehicles, or open land. Intense orange glow, smoke plumes.
- Characters/Specific Objects:
  Flames and smoke (distinct against backdrop). Panicked crowd, firefighters with hoses.
- Actions/Behaviors:
  Rapid fire spread. People fleeing with hands covering faces. Structural collapse or explosions within fire.

14. Ground Collapse
- Scene Environment:
  Urban roads, construction areas, or unstable terrain. Sudden appearance of sinkholes.
- Characters/Specific Objects:
  Sinking road surface, vehicles or people falling into cavities.
- Actions/Behaviors:
  Sudden downward cave-in of ground surface. People or vehicles swallowed rapidly. Surrounding crowd panicking and retreating.

15. Infrastructure Failure
- Scene Environment:
  Bridges, tunnels, dams, pipelines, power lines, or large public structures.
- Characters/Specific Objects:
  Cracking or collapsing structural elements, broken cables, flooding water.
- Actions/Behaviors:
  Progressive or sudden structural deformation. Debris falling into water or road. People evacuating rapidly from affected zone.

16. Landslide
- Scene Environment:
  Hillsides, mountain roads, or construction cuts after rain. Moving mass of earth/rock.
- Characters/Specific Objects:
  Descending soil/rock mass. Vehicles or structures buried. People fleeing uphill.
- Actions/Behaviors:
  Rapid downhill movement of earth. Objects/vehicles engulfed. Dust cloud raised on impact.

17. Leakage
- Scene Environment:
  Industrial plants, pipelines, chemical storage areas, or roads near tanker vehicles.
- Characters/Specific Objects:
  Visible liquid or gas release (dark liquid spreading, vapor cloud). Workers in protective gear.
- Actions/Behaviors:
  Spreading liquid stain or rising vapor. Workers evacuating or applying containment. Vehicles or people maintaining distance.

18. Medical Emergency
- Scene Environment:
  Public spaces (sidewalks, shopping areas, offices), sports venues.
- Characters/Specific Objects:
  Person collapsed or convulsing on ground. Bystanders kneeling around them. First responders arriving.
- Actions/Behaviors:
  Sudden collapse without apparent external cause. Bystanders gathering and gesturing for help. CPR motions or stretcher arrival.

19. Natural Disasters
- Scene Environment:
  Wide-area outdoor settings affected by earthquake, tornado, flood, or tsunami.
- Characters/Specific Objects:
  Collapsing buildings, rushing water, airborne debris, uprooted trees.
- Actions/Behaviors:
  Large-scale structural failure or environmental upheaval. Mass evacuation. People trapped under debris or swept by water.

20. Person Drowning
- Scene Environment:
  Pools, rivers, beaches, flooded areas. Water surface with agitation.
- Characters/Specific Objects:
  Person partially submerged or flailing. Bystanders on shore. Rescue equipment (rings, ropes, boats).
- Actions/Behaviors:
  Arm thrashing or sudden submersion. Failed swimming attempts. Rescuers diving in or throwing ropes.

21. Pushing Conflict
- Scene Environment:
  Crowded public areas (queues, protests, transit stations).
- Characters/Specific Objects:
  Two or more people in close contact, one or more being pushed. Crowd nearby.
- Actions/Behaviors:
  One person forcefully shoving another. Victim stumbling or falling. Crowd reacting or intervening.

22. Robbery
- Scene Environment:
  Streets, ATMs, retail stores, or vehicles. Fast-moving perpetrators.
- Characters/Specific Objects:
  Robber (masked/covered face, possible weapon). Victim handing over valuables. Stolen goods (bags, cash).
- Actions/Behaviors:
  Weapon brandishing or aggressive grabbing. Perpetrator fleeing rapidly. Victim cowering or chasing.

23. Safety Violations
- Scene Environment:
  Construction sites, factories, roads, or hazardous work zones.
- Characters/Specific Objects:
  Workers without proper PPE (no helmets, harnesses). Exposed hazardous materials or equipment.
- Actions/Behaviors:
  Workers performing high-risk tasks without protection. Near-miss incidents (close calls with machinery). Supervisors or colleagues reacting with alarm.

24. Slip and Fall Accident
- Scene Environment:
  Wet floors, icy surfaces, staircases, or uneven terrain.
- Characters/Specific Objects:
  Person falling; wet floor signs or ice patches may be visible.
- Actions/Behaviors:
  Sudden loss of balance and fall. Body impacting ground. Bystanders rushing to assist or calling for help.

25. Structural Failure
- Scene Environment:
  Buildings, bridges, retaining walls, or large installations under load or stress.
- Characters/Specific Objects:
  Cracking walls, collapsing floors, falling beams. People evacuating.
- Actions/Behaviors:
  Progressive cracking then sudden collapse. Dust cloud and debris scatter. People fleeing the affected structure.

26. Sudden Illness and Seizure
- Scene Environment:
  Public indoor or outdoor spaces (offices, streets, transit).
- Characters/Specific Objects:
  Person collapsed or convulsing. Bystanders surrounding them. Medical responders arriving.
- Actions/Behaviors:
  Uncontrolled limb movements (seizure) or sudden rigidity. Person falling without provocation. Crowd forming a protective ring.

27. Theft
- Scene Environment:
  Crowded areas (markets, transit), parking lots, or stores.
- Characters/Specific Objects:
  Perpetrator in close proximity to victim. Stolen item (bag, phone, wallet) transferred rapidly.
- Actions/Behaviors:
  Pickpocketing (hand reaching into pocket/bag). Item snatched and perpetrator walking/running away. Victim reacting with alarm.

28. Traffic Accident
- Scene Environment:
  Roads, intersections, highways. Skid marks, scattered debris, traffic congestion.
- Characters/Specific Objects:
  Colliding/overturned vehicles, deployed airbags. Injured pedestrians, emergency responders.
- Actions/Behaviors:
  Sudden vehicle swerving or collision. Bodies flung or vehicles spinning. Bystanders gathering; emergency vehicles arriving.

29. Vandalism
- Scene Environment:
  Public property (walls, vehicles, fences), abandoned buildings.
- Characters/Specific Objects:
  Perpetrator with spray cans, rocks, or tools. Defaced or broken property.
- Actions/Behaviors:
  Spraying walls, smashing glass with blunt objects. Quick escape after destruction. Onlookers pointing or shouting.

30. Weapons Incident
- Scene Environment:
  Public spaces (streets, transit, buildings) with sudden crowd panic.
- Characters/Specific Objects:
  Person holding or brandishing weapon (firearm, knife, blunt object). Victims retreating or falling.
- Actions/Behaviors:
  Weapon displayed or used aggressively. Crowd dispersing rapidly. Victims ducking, fleeing, or collapsing.

31. Wild Large Animal Intrusion
- Scene Environment:
  Urban streets, residential areas, farms, or public venues near wildlife zones.
- Characters/Specific Objects:
  Large animal (bear, elephant, deer, boar) in an urban or populated setting. People and vehicles nearby.
- Actions/Behaviors:
  Animal moving erratically through crowds. People fleeing or freezing in place. Animal charging vehicles, fences, or buildings.

Key Cross-Cutting Observations
- Panic Signifiers: Crowd scattering, limb flailing, or collapsing.
- Motion Clues: Sudden acceleration, unnatural trajectories, violent limb movements.
- Blur/Distance Adaptation:
  • Focus on contrast (fire/smoke, flash, dark liquid vs. background).
  • Detect shape deformities (overturned vehicles, slumped bodies, collapsed structures).
  • Track crowd motion anomalies (mass evacuation vs. directional fleeing).
'''

pistachio_prior_q = pistachio_prior_q + '\n' + q5
pistachio_prior_sq = pistachio_prior_q + '\n' + sq
pistachio_prior_dq = pistachio_prior_q + '\n' + draw_mask + q5