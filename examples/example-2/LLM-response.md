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
right_of(M2, M1) is less strict than same_row(M1, M2), because the latter forces exact horizontal alignment and reduces the solution space more significantly.

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

User 
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
m1 net1 ibias vdd! vdd! pmos
m2 net3 ibias vdd! vdd! pmos
m3 net5 ibias vdd! vdd! pmos
m4 net10 net12 vdd! vdd! pmos
m5 net6 net8 vdd! vdd! pmos
m6 net8 net8 vdd! vdd! pmos
m7 net8 net8 vdd! vdd! pmos
m8 net12 net12 vdd! vdd! pmos
m9 net11 net12 vdd! vdd! pmos
m10 ibias ibias net1 vdd! pmos
m11 net2 ibias net3 vdd! pmos
m12 net4 ibias net5 vdd! pmos
m13 net9 ibias net10 vdd! pmos
m14 output_n ibias net6 vdd! pmos
m15 net7 ibias net8 vdd! pmos
m16 output_p ibias net11 vdd! pmos
m17 net8 in1 net13 gnd! nmos
m18 net12 in2 net13 gnd! nmos
m19 net2 net2 gnd! gnd! nmos
m20 net13 net2 gnd! gnd! nmos
m21 net4 net4 net14 gnd! nmos
m22 net9 net4 net17 gnd! nmos
m23 output_n net4 net15 gnd! nmos
m24 net7 net4 net16 gnd! nmos
m25 output_p net4 net18 gnd! nmos
m26 net14 net14 gnd! gnd! nmos
m27 net17 net17 gnd! gnd! nmos
m28 net15 net17 gnd! gnd! nmos
m29 net16 net16 gnd! gnd! nmos
m30 net18 net16 gnd! gnd! nmos

{{STRUCTURE_RESULT}}

{{PARTITIONING_RESULT}}


Output
27,004t
Reasoning
Planning constraints and positioning

I need to keep my constraints list manageable and avoid overconstraining. It’s important to focus on clustering within blocks and establishing their relative positions or stages. Since I’m not partitioning, using cluster proximity for those blocks after orientation seems like a good approach. This way I can ensure organization without making things overly complicated. Let's keep things efficient and effective!

Organizing branches for mapping

I'm considering how to arrange the branches left to right. It seems like bias generators should be on the leftmost side. Then I could place the input differential pair core next to them. For outputs, I think I can arrange the output-related branches vertically to the right, with the left-side output_n column and the right-side output_p column. I'm also wondering about the auxiliary branches net7 and net9, which might fit well between the core and outputs or around them.

Evaluating output branches

I’m analyzing the output structure: the output_n branch is on the left side, driven by the left diff node net8, while the output_p branch is on the right, led by the right diff node net12. It seems to flow from left to right, with bias first, followed by output_n, the left diff side, tail centered, and then the right diff side leading to output_p. Still, having output_n on the left doesn't feel ideal to me.

Considering circuit design constraints

I'm thinking through how to layout this design, specifically with left and right branches and bias components. I want to ensure it's human-readable, so I need to capture robust constraints with supplies organized top to bottom in branches. The output branches should go to the right of the corresponding local bias. I must be careful not to over-constrain the components while ensuring they align properly. It seems like the order and strictness of positioning are vital for clarity.

Refining hierarchy relationships

I'm considering how to use the above relationships first, followed by same_column_above later, to refine the design. I want to avoid redundancy, so I need to think about a progression where above relationships define a vertical hierarchy within branches. For example, I can structure them like m1 above m10 and others in that manner. There's also a possibility that output_n could be placed properly in relation to m14 and m23, given they meet at the output node. This seems crucial for the schematic!

Structuring the schematic layout

In this transistor-level schematic, I need to position m14 above the output node and m23 below it, aligning m14 above m23. I’ll do something similar for m16, placing it above m25. This makes sense for maintaining an organized structure. Additionally, I should use left_of for stage separation, ensuring the bias branches are left of the differential pair and outputs. This organization can really help with clarity throughout the schematic!

Clarifying constraints for logic

I’m thinking about how to interpret the relationship between A and B. It could be confusing if they aren't in the same row, but maybe the columns matter more than the rows. I want to set constraints carefully to minimize ambiguity. Using conditions like "same_column_below" or "same_column_above" can help streamline things, especially when working with multi-element stacks. I think I can build those relationships systematically, ensuring clarity in my approach.

Organizing branch structures

I'm considering various bias branches, like m7 above m15 and m4 above m13. I also want to explore the arrangement of "diff input" branches with m6 above m17 and m8 above m18, along with a potential tail branch of m2 above m11. I think it’s important to establish a left-to-right order for the bias branches while ensuring separation between stages. It seems like m1 could be left of m2, and so on, creating a clearer structure. I’ll also confirm row alignments for better organization.

Considering channel placement

I’m thinking about the arrangement of the output channels related to the core. If both the output_n and output_p channels are to the right, it makes sense to position m17 and m18 on the left of these channels. I could also set m18 to the left of m7 and m4 since m7 represents a local branch for the left channel and m4 for the right channel. This structure might help clarify their relationships and functionality.

Evaluating layout options

I’m considering the placement of elements in my layout. I’ve established some relationships like m7 being left of m4, m5, and m9, and I’m trying to figure out their order. One thought is to group things strongly via cluster proximity or arrange the columns differently. Perhaps placing output_n and its local branch on the left while pushing output_p to the right would enhance readability. I want to find the best order for everything, including m15 and m13.

Structuring elements correctly

I’m working on the layout, and I’ve figured out that m13 should be part of the right local branch while m14 belongs to the left output. If the left channel is entirely on the left side of the right channel, then m14 can sit left of m13. I’ll need to ensure that local branches within each channel follow a top-down ordering in the same column. Also, should I consider m7 to be in the same row as m4?

Revising order parameters

I'm considering primitive order, which includes both "left_of" and "right_of." To simplify things, I wonder if I could just focus on using "left_of" only to avoid redundancy. It feels like a cleaner approach that might streamline the process. I'll need to evaluate if this change could affect the overall clarity or functionality, but there's something appealing about keeping it straightforward. Let's see how this could work out!

Considering column proximity

I'm thinking about using a column proximity of 2 between adjacent stage representative columns, like m3 and m6, or m8 and m7. However, the order suggests using row proximity and then column proximity before clustering. I also wonder if I really need column proximity. It might help keep the spacing compact for stages like m1-m2 through m4-m9, but left_of already defines order. I need to balance preventing excessive gaps versus clarity of the structure.

Considering spacing constraints

I’m exploring the idea of using row_proximity 1 for vertically adjacent elements in the same column. However, same_column_above does not dictate distance. It seems helpful to keep stacked branches compact with row_proximity 1 or 2. The relationship between these proximity parameters feels complex and might improve if applied correctly. I think using row_proximity 1 along with same_column_above could ensure better vertical adjacency, but I’m cautious about potentially overconstraining things if device heights are tall. It’s an interesting balance!

Considering the t-junction layout

I’m thinking about whether a t-junction requires A to be positioned between B and C on the same row. It seems likely that it would, so "A in between" might mean there's a column separating B and C. If m17 and m18 are adjacent, then that configuration wouldn't work. I'm glad I caught that detail! It's these little things that really matter in layout design.

Simplifying row constraints

I'm considering simplifying the same_row setup to focus on stage-specific rows. For example, I could use top bias like m1, m2, m3, mid bias like m10, m11, m12, and also include top diff like m6, m8 and diff pairs like m17, m18. Each right-side row chain can be defined, like row3 and row4 right-side. This approach might reduce constraints, but m20 could pose a challenge without a row3 anchor. I’m thinking of alternatives like combining m19, m20, and m20, m21.

Analyzing column arrangement

I’m thinking about how two components might fit together in the same column, either at row 1 or row 2. Clutter could be a concern, but it seems that the left side of the top columns doesn't quite allow that. The column order explicitly specifies that m6 is to the left of m8, and with a proximity of 2, there’s one empty column in between. So, it appears my arrangement holds up!

Evaluating amplifier design

I'm considering the fully differential folded cascode amplifier design, where it usually has a symmetric layout, with output_n on the left and output_p on the right, which gives a nice balance. The bias network would be on the left too. This layout might be the most human-readable option for clarity. It’s interesting to think about how visual symmetry can help in understanding the circuit better!

Considering symmetric layout

I'm thinking we should favor symmetry here. The developer mentioned aligning matched and symmetric devices and reflecting signal flow from left to right. In a differential pair, symmetry is essential. Maybe I should position the output_n branch on the left of the core and output_p on the right. Placing the bias network far left and the outputs mid-left and right seems logical. So, I’m arranging the components in a way that keeps the channel association preserved. Overall, this layout looks pretty neat!

Reassessing layout structure

I need to keep the differential columns m6 and m8 separated by the tail gap. The second row will include components like m10, m11, m12, and so forth. By arranging them this way, I can keep output_n adjacent to the left of the tail and output_p on the right, which looks nice. Now, I’m considering if this setup will affect signal flow. Inputs could be on the left, with the differential pair centered and outputs on both sides. Adopting this symmetrical layout should align with the developer's emphasis on structural hierarchy and symmetry.

Considering configuration order

I'm thinking through the right-side symmetric configuration and noting that I've got diff_right, output_p, and local_p. For the top order, I believe it’s m1, m2, m3, m7, m5, m6, m8, m9, and m4, and I'm pondering if local_p should be on the outer right. I’m questioning whether output_p needs to be adjacent to diff_right; maybe it does? I’ll need to clarify that to ensure it all fits together correctly!

Organizing stage groupings

I'm considering how to compare the stage groupings. There's the bias stage on the left with three columns, and then the left output/local stage, which has two columns in the middle-left. The input core is in the center with two columns and a tail, while the right output/local stage is in the middle-right with another two columns. This setup seems effective and organized!

Evaluating column proximity

I’m looking at the column proximity values and considering how they relate. It seems like I could order them based on their strictness, with 1 being stricter than 2. Maybe I should list the values within the same primitive from looser to tighter, but I wonder if I should prioritize 2 first since the guidelines suggest a progression from relaxed to strict. Using all 2s might simplify things, but I’ll keep an eye on potential over-constraining.

Finalizing row and column proximity

I'm deciding to keep 2 for consistency to avoid sorting by n. It seems row_proximity 1 is necessary, and I think it might be sufficient to use representative columns like m3, m12, m21, m26. I don’t believe cluster_proximity is needed after column_proximity. For the t_junction, I'll build the final list carefully with the exact syntax.

I want to ensure row constraints are clear for all rows, and maybe I should adjust the order for row4 to follow a left-to-right sequence.

assistant
constraints = [
["left_of", "m1", "m2"],
["left_of", "m2", "m3"],
["left_of", "m3", "m7"],
["left_of", "m7", "m5"],
["left_of", "m5", "m6"],
["left_of", "m6", "m8"],
["left_of", "m8", "m9"],
["left_of", "m9", "m4"],

["same_row", "m1", "m2"],
["same_row", "m2", "m3"],
["same_row", "m3", "m7"],
["same_row", "m7", "m5"],
["same_row", "m5", "m6"],
["same_row", "m6", "m8"],
["same_row", "m8", "m9"],
["same_row", "m9", "m4"],

["same_row", "m10", "m11"],
["same_row", "m11", "m12"],
["same_row", "m12", "m15"],
["same_row", "m15", "m14"],
["same_row", "m14", "m17"],
["same_row", "m17", "m18"],
["same_row", "m18", "m16"],
["same_row", "m16", "m13"],

["same_row", "m19", "m21"],
["same_row", "m21", "m24"],
["same_row", "m24", "m23"],
["same_row", "m23", "m20"],
["same_row", "m20", "m25"],
["same_row", "m25", "m22"],

["same_row", "m26", "m29"],
["same_row", "m29", "m28"],
["same_row", "m28", "m30"],
["same_row", "m30", "m27"],

["same_column_above", "m1", "m10"],
["same_column_above", "m2", "m11"],
["same_column_above", "m11", "m19"],
["same_column_above", "m3", "m12"],
["same_column_above", "m12", "m21"],
["same_column_above", "m21", "m26"],
["same_column_above", "m7", "m15"],
["same_column_above", "m15", "m24"],
["same_column_above", "m24", "m29"],
["same_column_above", "m5", "m14"],
["same_column_above", "m14", "m23"],
["same_column_above", "m23", "m28"],
["same_column_above", "m6", "m17"],
["same_column_above", "m8", "m18"],
["same_column_above", "m9", "m16"],
["same_column_above", "m16", "m25"],
["same_column_above", "m25", "m30"],
["same_column_above", "m4", "m13"],
["same_column_above", "m13", "m22"],
["same_column_above", "m22", "m27"],

["row_proximity", 1, "m3", "m12"],
["row_proximity", 1, "m12", "m21"],
["row_proximity", 1, "m21", "m26"],

["column_proximity", 2, "m1", "m2"],
["column_proximity", 2, "m2", "m3"],
["column_proximity", 2, "m3", "m7"],
["column_proximity", 2, "m7", "m5"],
["column_proximity", 2, "m5", "m6"],
["column_proximity", 2, "m6", "m8"],
["column_proximity", 2, "m8", "m9"],
["column_proximity", 2, "m9", "m4"],

["t_junction", "m20", "m17", "m18"]
]


Conversation History: resp_0ae1d8c3e0a2b57d0069daae69ce688191915c7f40691ce8cf