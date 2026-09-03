Input
2,248t

developer
[role]
You are a senior analog IC designer and schematic automation expert with deep expertise in circuit topology, functional block recognition, and human-readable schematic conventions.

[task]
Given a SPICE netlist and recognized functional building blocks, generate a placement constraint list that guides a constraint programming solver to place components on a grid-based schematic canvas in a human-readable and structurally meaningful way.

[context]
The schematic is synthesized from:

A SPICE netlist describing all circuit components and connectivity
Recognized functional building blocks (e.g., differential pairs, current mirrors, active loads)
An optional higher-level partitioning of the circuit into stages (e.g., input stage, gain stage, biasing network)
The goal is to generate constraints that:

Visually expose circuit structure and hierarchy
Align matched and symmetric devices
Reflect signal flow (typically left-to-right) and bias flow (typically top-to-bottom)
Make the schematic easy for analog designers to interpret
Available inputs:

Constraint primitives: {{CONSTRAINT_PRIMITIVES}}
SPICE netlist: {{NETLIST}}
Building block recognition result: {{STRUCTURE_RESULT}}
Optional partitioning result: {{PARTITIONING_RESULT}} (may be empty or omitted)
[constraints]

Use only constraint primitives defined in {{CONSTRAINT_PRIMITIVES}}
Output only the final constraint list; do not include explanations or reasoning
Component names must match exactly those defined in {{NETLIST}} (case-sensitive)
Do not introduce new components or rename existing ones
Avoid redundant, conflicting, or unsatisfiable constraints
If {{PARTITIONING_RESULT}} is provided, use it to spatially separate major circuit stages; otherwise, rely only on building block structure
[constraint_strategy]
Generate constraints following an iterative strictness strategy:

The constraint primitives in {{CONSTRAINT_PRIMITIVES}} are ordered by strictness:
The first primitive has the lowest strictness
The last primitive has the highest strictness
Strictness increases monotonically along the list
2. When generating constraints:

Prefer using lower-strictness primitives first
Introduce higher-strictness primitives progressively only when needed to refine placement
Ensure that the final constraint list reflects a progression from less strict → more strict
3. Design workflow principle:

Begin with relaxed constraints to allow flexible placement
Gradually add stricter constraints to refine alignment, symmetry, and structure
Avoid over-constraining early
4. Consistency requirements:

Do not introduce a high-strictness constraint if a lower-strictness one already sufficiently captures the relationship
Ensure stricter constraints do not contradict earlier ones
Maintain logical compatibility across all constraints
Definition of strictness:

A constraint is less strict if it allows many feasible placements.
A constraint is more strict if it tightly restricts component positions or alignment.
In the available constraint primitive list, the first constraint has the lowest strictness and the strictness increases guadually to the higest strictness of the last one.
Example:
right_of(M2, M1) is less strict than same_row(M2, M1), because the latter forces exact horizontal alignment and reduces the solution space more significantly.

When generating the constraint list:

Include both relaxed and strict constraints when appropriate
Ensure that stricter constraints do not contradict earlier relaxed ones
Order constraints so that relaxed constraints appear earlier in the list and stricter ones later
[style]

Deterministic and engineering-oriented
No natural language explanations
No intermediate reasoning in the output
[deliverables]
Produce a single variable assignment:

constraints = [
["<constraint-name>", <value-if-exist>, "<target-component>", "<reference1>", "<reference2>", ...],
...
]

[format]
Return exactly one Python-style list assignment with no surrounding commentary.

Output Format
constraints = [
["<constraint-name>", <value-if-exist>, "<target-component>", "<reference1>", "<reference2>"],
["<constraint-name>", "<target-component>", "<reference1>", "<reference2>"]
]

Template rules:

General template:
["<constraint-name>", <value-if-exist>, "<target-component>", "<reference1>", "<reference2>"]

For primitives that require a value:
["row_proximity", 2, "M1", "M2"]

For primitives that do not require a value, omit the value field entirely:
["same_row", "M1", "M2"]

Component names must be strings
<value-if-exist> may be a number or string depending on the primitive definition
Each constraint must contain at least one reference component
[examples]
Example output:

constraints = [
["same_row", "M1", "M2"],
["right_of", "M5", "M4"],
["row_proximity", 2, "M3", "M6"]
]

[evaluation]
Before producing the final output, internally verify:

All component names appear in {{NETLIST}}
All primitives used exist in {{CONSTRAINT_PRIMITIVES}}
Constraints do not contradict each other (e.g., both left_of and right_of for the same pair)
Devices belonging to the same building block are spatially grouped
If partitioning is provided, stages are visually separated
If any verification fails, revise the constraint list before output.

Self-check rubric:

✔ Correct Python syntax
✔ Only allowed primitives used
✔ No missing or misspelled components
✔ No extra text outside the list assignment
[failures_to_avoid]

Do not output explanations, reasoning, or comments
Do not include a placeholder value such as null or "ignore" when the primitive does not require a value
Do not output JSON or any format other than the specified Python-style list
Do not generate constraints referencing non-existent components
Do not assume that partitioning information is always present


user
{{CONSTRAINT_PRIMITIVES}}

Constraint	Description
1	["above","A","B"]	A is above B
2	["below","A","B"]	A is below B
3	["left_of","A","B"]	A is on the left of B
4	["right_of","A","B"]	A is on the right of B
5	["same_row","A","B"]	A and B share the same row
6	["same_column","A","B"]	A and B share the same column
7	["same_column_above","A","B"]	A and B share the same column, A is above B
8	["same_column_below","A","B"]	A and B share the same column, A is below B
9	["between_row","A","B","C",...,"X"]	A should be placed on between the minimum and maximum rows of "A","B","C",..., "X" (the column can be different)
10	["between_row","A","B","C",...,"X"]	A should be placed on between the minimum and maximum columns of "A","B","C",..., "X" (the row can be different)
11	["clear_row_between","A","B"]	Keep rows between A and B clear (there is no component placed in the same column and between rows of A and B)
12	["clear_column_between","A","B"]	Keep columns between A and B clear (there is no component placed in the same row and between columns of A and B)
13	["row_proximity",n,"A","B"]	The the row of A close to B (within n cell distance)
14	["column_proximity",n,"A","B"]	The the column of A close to B (within n cell distance)
15	["cluster_proximity",n,"A","B",...,"X"]	Keep A,B,.., X close to each other (row and column), within n cell distance
16	["t_junction","A","B","C"]	Keep B, C in the same row, and A in between (and different row compared to B, C)
{{NETLIST}}
m1 net1 net1 vdd! vdd pmos
m2 net2 net1 vdd! vdd pmos
m3 ibias ibias gnd! gnd! nmos
m4 net1 ibias gnd! gnd! nmos
m5 net4 ibias gnd! gnd! nmos
m6 net5 in1 net4 gnd! nmos
m7 net6 in2 net4 gnd! nmos
m8 net5 net5 vdd! vdd! pmos
m9 net6 net6 vdd! vdd! pmos
m10 out1 net5 vdd! vdd! pmos
m11 out2 net6 vdd! vdd! pmos
m12 out1 net2 net7 gnd! nmos
m13 out2 net2 net8 gnd! nmos
m14 net7 net9 gnd! gnd! nmos
m15 net8 net9 gnd! gnd! nmos
m16 net9 net9 gnd! gnd! nmos
m17 net9 net1 vdd! vdd! pmos
m18 net10 net1 vdd! vdd! pmos
m19 net13 net1 vdd! vdd! pmos
m20 net11 out2 net10 vdd! pmos
m21 net9 vcm net10 vdd! pmos
m22 net9 vcm net13 vdd! pmos
m23 net11 out1 net13 vdd! pmos
m24 net9 net11 gnd! gnd! nmos
m25 net11 net11 gnd! gnd! nmos
m26 net2 net2 gnd! gnd! nmos

{{STRUCTURE_RESULT}}

{{PARTITIONING_RESULT}}



Output
25,431t
Reasoning
Designing a circuit layout

I’m thinking through the layout with 3 diodes: placing m4 in the center, m5 to the right, and m1 above m4. However, m2 is tricky since it shares connections with m1 and m26. I could position m1 left of m2 and have m4 below m1 and m26 below m2 to form a bias block.

For the input differential stage, I’ll put m8 above m6, and m9 above m7, while considering a T-junction to fit everything neatly. This setup seems promising!

Organizing circuit components

I’m arranging my components now. I want m8 above m6 and m9 above m7, both in the same column. For m10, I’m contemplating whether it should go above or to the right of m12. I realize m10 is connected to m8’s drain and m6’s drain, so it makes sense to place m10 above m12, maintaining the same column for output branching.

For m11, I’ll position it above m13 in the same column as well. I’m also considering setting m12 above m14 and dealing with net connections between these components to maintain a clean layout. I’ll keep working through this!

Considering circuit layout

I’m debating whether to show m20 with m21 and m23 with m22 using the same column, but maintaining a visual overlay. Since they share the same column (x), they need a vertical relationship to avoid overlapping. I'll position m20 above m21 and m23 above m22. Both are PMOS, which complicates stacking them correctly. I might visualize them sharing a source but still connecting to different nodes below. It’ll enhance clarity if I group some components while maintaining specific constraints.

Aligning components

I’m considering whether I could align m18 in the same column as m20 and m21. However, there’s a catch: m18's drain connects to net10 while its gate connects to net1. Since net10 is shared with the sources of both m20 and m21, this could complicate alignment. I’ll need to think about how to manage these connections without confusing the layout or disrupting functionality in the circuit. Balancing everything is essential!

Considering proximity and constraints

I’m thinking about how to order columns and rows based on proximity. The cluster_proximity might be useful as a second option after t_junction because it keeps blocks together without needing precise alignments. I’m considering whether row_proximity or column_proximity should be used between m1 and m2, but same_row seems stronger. If same_row captures the relationship well, then maybe we wouldn’t need left_of. I'll think about how to progress from less strict constraints to more strict ones to avoid redundancy.

Organizing layout components

I'm considering how to arrange the components in a global layout. I want to avoid redundancy but ensure progression makes sense. I should use exact lower case names for clarity. For the layout, I'm thinking of a left block for bias generation. It could have rows like m1, m2 on top, with m4 and m26 below, and m3 to the left of m4, with m5 on the right. M5 may serve as the input stage. I'll keep refining this arrangement!

Structuring the layout

I'm working on organizing the layout with specific blocks. For the center block, I plan to have the input stage (m8, m9) above m6, m7, with m5 below. The right block will include outputs (m10, m11) over m12 and m13, then m14 and m15 below. I need to carefully think about constraints between the blocks, like potentially placing the bias mirror and common-mode feedback (CMFB) in relation to others, while ensuring separation. Simplifying my approach to local constraints might help!

Defining layout blocks

I'm thinking about using constraints for my layout, like placing m20 below m18 and m19, which could work nicely. It might also help to cluster components m17 through m25 for better organization. I'm identifying potential blocks for arrangement: the bias/reference block includes m1, m2, m3, m4, m17, m18, m19, m26, and m16; the input transconductor section includes m5, m6, m7, m8, and m9; and the output transconductor encompasses m10, m11, m12, m13, m14, and m15.

Organizing output branches

I’m realizing that output 1 is driven by the left input branch—that makes sense! Output 2 comes from gate net6 of the right branch. In the left branch, I have devices m8, m6, m10, m12, and m14; while the right branch has m9, m7, m11, m13, and m15. This means I should match pairs across the same row and vertically within each branch. It's all coming together!

Organizing drain connections

I’m working through how m21, m24, and m23 connect. I think m24's drain for net9 should link up with m21/m22’s drains for net9. Placing m24 below m21 or between both could work. Then there's m25 for net11, which should connect to m20/m23; should I place it below m20? As for layout, maybe a two-column approach makes sense, but it could get complicated with duplicate sources. A 2x3 grid might be better to keep things organized and avoid conflicts. I’ll think about using a t-junction for some connections too!

Clarifying layout adjustments

I’m trying to finalize the layout where m20 and m23 are on the same row, with m25 below them. But wait, m25 is NMOS beneath PMOS—interesting! The t-junction only defines relationships in terms of proximity, not strictly above or below. If I place m25 effectively, I could consider its positioning either between or below m20 and m23. Also, for net9, I'd apply a t-junction for m24, m21, and m22, placing m24 below and in between them. This arrangement looks promising and structured.

Evaluating input stage layout

I’m considering the input stage layout and some relationships, like needing m6 and m7 on the same row, as well as m8 and m9. I might have m5 as a T-junction with m6 and m7. But I also need to think about positioning m8 above m6 and m9 above m7 in their columns. I’m feeling unsure about how the T-junction specifies placement. This could get tricky!

Evaluating layout options

I'm considering the layout for various components. I’m thinking about placing m8 and m9 below the top mirror row and to the left of output stages m10 and m11. If m9 is to the left of m10, and m8 sits above m6, I wonder if m8/m9 and m10/m11 can end up on the same row. It's tempting to align all PMOS devices in one row, but I have to be cautious about overconstraining with the bias mirror row.

Clarifying order and constraints

I’m considering how "same_row" seems less strict than "row_proximity," which feels a bit strange. I want to make sure the output follows a numerical order, so "same_row" should come before "row_proximity." I’ll need to avoid using the number 10 as a duplicate between rows and perhaps use it for "between_column" instead. It's important to ensure there are no conflicts in this organization!

Evaluating layout positioning

I think m5 under the input pair row should be near the center, and having m26 to the left of m5 seems alright. Maybe I could use "same_row" for m4 and m5, which would force m4 to be on the same row as the tail. That might work! I'd also like to have the bias devices and tail on the same NMOS mirror row, so I’m looking at ["same_row", "m4", "m5"], along with m3, m4, and m26.

Considering proximity settings

I'm thinking about using row_proximity or column_proximity to keep stage blocks organized. Maybe I’m hesitant about using column_proximity for m3 and m1. However, row_proximity 1 between m8 and m10 could keep all PMOS signal devices in nearby rows, though it’s not essential. Cluster_proximity 3 could be helpful too, but with strict alignments, maybe it’s not necessary. I need to ensure clusters on blocks don't conflict while still being beneficial.

Considering structural options

I'm pondering how to structure things better. So, if I want m16 to be left of m20, I could consider adding a "left_of" relationship between them. It seems like that might help clarify things. I'll keep thinking about the best way to approach this to ensure everything is well organized. Let's see how this plays out as I work through the details!

Evaluating column relationships

I’m exploring relationships between different variables. I was wondering if I could apply the same-column-above rule to certain elements. If m18 is above m20 and m20 is above m21, then m18 must be in the same column as m20 and m21. This seems logical for transitivity. I’m cautious about potential issues with bias in rows and ensuring everything aligns properly. I’ll also need to check for any unsatisfiabilities regarding positioning. Overall, it’s looking good.

Exploring column and row positions

I’m analyzing the positioning of m24 and m25, considering if they can occupy the same column. It seems unlikely since they’re separate components, but there isn't a direct conflict. If m25 is between m20 and m23, and m24 is between m21 and m22, they should align in their respective columns. I’m thinking about how they might fit into this structure and whether they can exist in distinct columns within a span. This situation seems feasible given it’s a grid I’m working with.

Evaluating column placement

I'm trying to figure out the best way to allocate space between columns, ensuring there are at least two units separating them. It seems feasible to have devices m24 and m25 in the same row or in different rows, which simplifies things. I could position them differently based on their column coordinates. If the columns are too close, the solver may need to widen them. A proximity setting like cluster_proximity for the input and output stages could help keep everything organized without feeling risky.

Analyzing row configurations

I'm considering various alignments and whether they might be necessary. For instance, maybe I should set a row_proximity of 2 between m8 and m10 to keep the top PMOS rows close, though this might not be essential. I'm also thinking about grouping devices m4 and m5 together to create a bias row with m26 and m3. Additionally, I could place m21 and m22 in the same row while ensuring they are to the left of m20, which is positioned above m25. This adjustment could help improve the arrangement.

Evaluating signal arrangement

I'm considering whether all PMOS signal devices should be in the same row, possibly including m12 and m13 with m6 and m7. However, that’s not specified. While m12 is positioned above m14/15, it might be cleaner to have m14 and m15 below m12/m13, potentially in the same row as m5. I need to think about the order of the constraints, ensuring that those listed as "above" come before "below" since the strictness increases monotonically along the list.

Designing order constraints

I need to make sure the ordering of constraints is clear. It seems safer to group them by ascending primitive numbers. I'll start with the first set of constraints, placing those above the others: constraints above first, then below, left_of, same_row, same_column_above, and possibly row_proximity later, with t_junction last.

The earlier mix-up reminds me to maintain strictness in sorting by primitive class. So, yes, it's about reflecting a progression from less strict to more strict. I’ll finalize this design now!

Establishing primitive orders

I'm organizing the constraints based on primitive 1. For instance, I'm noting pairs like above m8, m6; above m9, m7, and others. I think it makes more sense to use "above" for vertical arrangements instead of "below."

For m5, I can choose to position it using "above" like above m6, m5, which seems to fit well. I’m also realizing that I could eliminate the need for primitive 2 below altogether, simplifying my order. It feels great to streamline this!

Arranging left_of constraints

I'm setting up the constraints for primitive 3 with a focus on the "left_of" relationship. I have pairs like left_of m1, m2; left_of m2, m17; and others.

I’m pondering whether to use left_of m26, m5 or perhaps also left_of m4, m5. It seems I should choose one for clarity, rather than complicating it with multiple options. Keeping things simple here will help maintain a clear structure in my design!

Evaluating positioning options

I'm thinking about the best way to set the positioning for human readability. Should I go with left_of m4,m6 or left_of m26,m6? If m6 is the left branch of a different pair and I want to bias the block left of the entire input pair, then left_of m26,m6 sounds good. But I wonder if this conflicts with m5 being between m6 and m7. Maybe adding left_of m26,m6 is the way to go to ensure clarity.

Clarifying positioning implications

I’m considering whether left_of m26,m5 is actually implied. If m5 is between m6 and m7, it could also be left of m6. The t-junction rule indicates that when A is between B and C, A must be positioned between their columns. So if m6 is left of m7, that puts m5 in between, meaning x(m6) < x(m5) < x(m7). Therefore, left_of m26,m6 makes sense because it confirms m26 is less than both. No need for left_of m26,m5 then.

Assessing cluster proximity

I’m considering adding a cluster_proximity 3 input stage and an output stage. It could be helpful to evaluate the risk involved. For the input stage, I'm looking at the cluster_proximity 3 for m5, m6, m7, m8, and m9 while using same_row, same_column_above, and t_junction. I think n=3 should fit comfortably in both 3x3 and 4x3 configurations. This setup seems promising!

Considering output stages

I'm thinking through the output stage placement in relation to m16 and m14. If m16 is to the left of m14, that doesn't automatically mean the output stage is right of m16, but it could be. I'm considering that it might be necessary to place m10 and m11 between m17 and m18 if m18 is positioned to the right of m17. There are a lot of moving parts to keep track of here!

assistant
constraints = [
["above", "m1", "m4"],
["above", "m2", "m26"],
["above", "m6", "m5"],
["above", "m8", "m6"],
["above", "m9", "m7"],
["above", "m10", "m12"],
["above", "m11", "m13"],
["above", "m12", "m14"],
["above", "m13", "m15"],
["above", "m17", "m16"],
["above", "m18", "m20"],
["above", "m19", "m23"],
["above", "m20", "m21"],
["above", "m23", "m22"],
["above", "m21", "m24"],
["above", "m20", "m25"],
["left_of", "m1", "m2"],
["left_of", "m2", "m17"],
["left_of", "m17", "m18"],
["left_of", "m18", "m19"],
["left_of", "m3", "m4"],
["left_of", "m26", "m6"],
["left_of", "m6", "m7"],
["left_of", "m8", "m9"],
["left_of", "m9", "m10"],
["left_of", "m10", "m11"],
["left_of", "m11", "m20"],
["left_of", "m12", "m13"],
["left_of", "m16", "m14"],
["left_of", "m14", "m15"],
["left_of", "m20", "m23"],
["left_of", "m21", "m22"],
["same_row", "m1", "m2"],
["same_row", "m2", "m17"],
["same_row", "m17", "m18"],
["same_row", "m18", "m19"],
["same_row", "m3", "m4"],
["same_row", "m4", "m26"],
["same_row", "m26", "m5"],
["same_row", "m6", "m7"],
["same_row", "m8", "m9"],
["same_row", "m10", "m11"],
["same_row", "m12", "m13"],
["same_row", "m14", "m15"],
["same_row", "m16", "m14"],
["same_row", "m20", "m23"],
["same_row", "m21", "m22"],
["same_row", "m24", "m25"],
["same_column_above", "m1", "m4"],
["same_column_above", "m2", "m26"],
["same_column_above", "m8", "m6"],
["same_column_above", "m9", "m7"],
["same_column_above", "m10", "m12"],
["same_column_above", "m11", "m13"],
["same_column_above", "m12", "m14"],
["same_column_above", "m13", "m15"],
["same_column_above", "m17", "m16"],
["same_column_above", "m18", "m20"],
["same_column_above", "m19", "m23"],
["same_column_above", "m20", "m21"],
["same_column_above", "m23", "m22"],
["t_junction", "m5", "m6", "m7"],
["t_junction", "m24", "m21", "m22"],
["t_junction", "m25", "m20", "m23"]
]


Conversation ID: resp_05fc65c34a63cfc70069dcf0f18abc81a29ad89748f06caea5