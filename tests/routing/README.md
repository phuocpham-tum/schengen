The test case has not created yet (and is subject for future work #TODO). 
But this directory contains all relevant input SPICE netlists, configuration files, and baseline results for future comparisons.

When working on routing and use this example as a test case, please (manually) pay attention to the following nets: (make sure there are no weird Steiner-like tree, no redundant loops, etc. )

```
"net_output_0"
"net_internal_1"
"net_internal_11"
"net_internal_6"
"net_supply_1"
"net_internal_10"
```

Expected outputs:

"routing_cost": 122877,
"num_bends": 149,
"num_crossings": 151,
"hpwl_cost": 545,