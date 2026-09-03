// Store grid data
document.body.style.zoom="67%";

const gridData = new Map();
let currentRows = 6;
let currentCols = 8;
let latestSchengenResultPath = null;
let componentPlacementData = {}; // global variable to store the current component placement data, which is a dictionary with key as component name, and value as an array of [row, col, orientation, type]
// routingData = {}; // global variable to store the current routing data, which is a dictionary with key as net name, and value as an array of coordinate points that form the routed path for that net. Each coordinate point is an array of [x, y] with origin at bottom-left and 100 units per grid cell
let routedNetsData = {};
let intersectionPointsData = {};


// Initialize grid on load
window.addEventListener('DOMContentLoaded', () => {
    createGrid();
});

function createGrid() {
    const rows = parseInt(document.getElementById('rows').value);
    const cols = parseInt(document.getElementById('cols').value);
    
    if (rows < 1 || cols < 1 || rows > 50 || cols > 100) {
        alert('Please enter valid grid dimensions (1-50 rows, 1-100 columns)');
        return;
    }

    currentRows = rows;
    currentCols = cols;

    const canvas = document.getElementById('gridCanvas');
    canvas.innerHTML = '<div id="routingLayers"></div>';
    
    // Set canvas dimensions
    const canvasWidth = cols * 100 * 0.5;
    const canvasHeight = rows * 100 * 0.5;
    canvas.style.width = canvasWidth + 'px';
    canvas.style.height = canvasHeight + 'px';

    // Set routing layer container dimensions
    const routingLayers = document.getElementById('routingLayers');
    routingLayers.style.width = canvasWidth + 'px';
    routingLayers.style.height = canvasHeight + 'px';

    // Clear routing layer toggle list on grid recreation
    const routingLayerList = document.getElementById('routingLayerList');
    if (routingLayerList) {
        routingLayerList.innerHTML = '';
    }

    // Create grid cells
    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
            const cell = document.createElement('div');
            cell.className = 'grid-cell';
            cell.dataset.row = row;
            cell.dataset.col = col;
            
            // Position from bottom-left (0,0)
            const x = col * 100 * 0.5; // Scale down to fit
            const y = (rows - 1 - row) * 100 * 0.5; // Flip Y axis so 0 is at bottom
            
            cell.style.left = x + 'px';
            cell.style.top = y + 'px';
            
            // Add label
            const label = document.createElement('div');
            label.className = 'cell-label';
            label.textContent = `(${row},${col})`;
            cell.appendChild(label);
            
            // Add click handler
            cell.addEventListener('click', (e) => {
                if (e.target.classList.contains('remove-btn')) return;
                // clear previous selection
                const prev = document.querySelector('.grid-cell.selected');
                if (prev && prev !== cell) prev.classList.remove('selected');

                document.getElementById('targetRow').value = row;
                document.getElementById('targetCol').value = col;

                // toggle selection if this cell contains a component
                if (cell.dataset && cell.dataset.compName) {
                    cell.classList.toggle('selected');
                    const comp = cell.dataset.compName;
                    document.getElementById("info").innerHTML = `<strong>Selected component</strong>: ${comp} @ (${row}, ${col})`;
                } else {
                    document.getElementById("info").innerHTML = `<strong>Selected gird cell</strong>: row, col = (${row}, ${col})`;
                }
            });
            
            canvas.appendChild(cell);
            
            // Restore image if exists
            const key = `${row},${col}`;
            if (gridData.has(key)) {
                addImageToCell(cell, gridData.get(key));
            }
        }
    }
}

// Adjust number of columns to fit available canvas width
function adjustGridColsToFit() {
    const canvasColumn = document.getElementById('canvasColumn');
    const colsInput = document.getElementById('cols');
    if (!canvasColumn || !colsInput) return;

    // cell width used in createGrid() is 50px (cols * 100 * 0.5)
    const cellWidth = 50;
    // available width inside the canvas column (account for borders/padding)
    const availableWidth = Math.max(1, canvasColumn.clientWidth - 8);
    let newCols = Math.max(1, Math.floor(availableWidth / cellWidth));

     if (newCols > 100) {
         newCols = 100; // enforce maximum column limit accepted by createGrid()
     }
     if (newCols < 40) {
         newCols = 40; // enforce minimum column limit to ensure usability of the grid
     }

    const currentCols = parseInt(colsInput.value, 10) || 0;
    if (newCols !== currentCols) {
        colsInput.value = newCols;
        // recreate grid to match new column count
        createGrid();
        // if we have placement data from server, redraw components
        if (typeof componentPlacementData !== 'undefined' && Object.keys(componentPlacementData).length > 0) {
            drawComponents(componentPlacementData);
        }

        // if we have routing data from server, redraw routed nets
        if (routedNetsData && typeof routedNetsData === 'object') {
            drawRoutedNets(routedNetsData, intersectionPointsData);
        }
        else
        {
            console.warn("No valid routing data found in server response:", routedNetsData);
        }

    }
}

function scheduleGridColumnResize() {
    if (typeof __adjustGridColsDebounce !== 'undefined' && __adjustGridColsDebounce) {
        clearTimeout(__adjustGridColsDebounce);
    }
    __adjustGridColsDebounce = setTimeout(() => {
        try {
            adjustGridColsToFit();
        } catch (e) {
            console.error(e);
        }
    }, 150);
}

// debounce resize handling
let __adjustGridColsDebounce = null;
window.addEventListener('resize', () => {
    scheduleGridColumnResize();
});

window.addEventListener('schematic:layoutchange', () => {
    scheduleGridColumnResize();
});

// Also call once on load to ensure initial sizing fits
window.addEventListener('DOMContentLoaded', () => {
    // small timeout to allow layout to settle
    setTimeout(adjustGridColsToFit, 50);
});

window.addEventListener('load', () => {
    const canvasColumn = document.getElementById('canvasColumn');
    const constraintsColumn = document.getElementById('constraintsColumn');
    if (typeof ResizeObserver === 'undefined') {
        return;
    }

    const observer = new ResizeObserver(() => {
        scheduleGridColumnResize();
    });

    if (canvasColumn) {
        observer.observe(canvasColumn);
    }
    if (constraintsColumn) {
        observer.observe(constraintsColumn);
    }
});

function insertImage() {
    const row = parseInt(document.getElementById('targetRow').value);
    const col = parseInt(document.getElementById('targetCol').value);
    //const imageUrl = "static/nmos-gate-left.png"; //document.getElementById('imageUrl').value.trim();

    // get selected component from dropdown
    const componentSelect = document.getElementById('componentSelect');
    const selectedValue = componentSelect.value;
    let imageUrl = "";
    if (selectedValue === "cap") {
        imageUrl = "static/cap.png";
    } else if (selectedValue === "resistor") {
        imageUrl = "static/resistor.png";
    }
    else if (selectedValue == "undefined") {
        imageUrl = "";
        Swal.fire({
            icon: 'error',
            title: 'Invalid component selection',
            text: 'Please select a valid component from the dropdown.',
        });
        return;

    } else if (selectedValue) {
        imageUrl = `static/${selectedValue}`;
    }


    if (!imageUrl) {
        alert('Please select a component from the dropdown: ' + imageUrl );
        return;
    }

    if (row < 0 || row >= currentRows || col < 0 || col >= currentCols) {
        alert(`Please enter valid coordinates (rows: 0-${currentRows-1}, cols: 0-${currentCols-1})`);
        return;
    }

    // Find the cell
    const cell = document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
    if (!cell) {
        alert('Cell not found');
        return;
    }

    // Store in grid data
    const key = `${row},${col}`;
    gridData.set(key, imageUrl);

    // Add image to cell
    addImageToCell(cell, imageUrl);
}

function addImageToCell(cell, imageUrl) {
    // Remove existing image if any
    const existingImg = cell.querySelector('img');
    const existingBtn = cell.querySelector('.remove-btn');
    if (existingImg) existingImg.remove();
    if (existingBtn) existingBtn.remove();

    // Create image element
    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = 'Grid image';
    img.onerror = () => {
        img.alt = 'Failed to load';
        img.style.display = 'none';
        alert('Failed to load image. Please check the URL.');
    };

    // Create remove button
    const removeBtn = document.createElement('button');
    removeBtn.className = 'remove-btn';
    removeBtn.textContent = '×';
    removeBtn.title = 'Remove image';
    removeBtn.onclick = (e) => {
        e.stopPropagation();
        const row = cell.dataset.row;
        const col = cell.dataset.col;
        const key = `${row},${col}`;
        gridData.delete(key);
        img.remove();
        removeBtn.remove();
        cell.classList.remove('has-image');
    };

    cell.appendChild(img);
    cell.appendChild(removeBtn);
    cell.classList.add('has-image');
}

function clearGrid() {
    gridData.clear();
    createGrid();
}

function changeGridSize() {
    // Use SweetAlert2 to prompt the user for a new grid size, first ask for the number of rows, then ask for the number of columns
    const rows = parseInt(document.getElementById('rows').value);
    const cols = parseInt(document.getElementById('cols').value);
    
    Swal.fire({
    title: 'Change Grid Size',
    html: `
        <input type="number" id="rowsInput" class="swal2-input" placeholder="Number of rows" value="${rows}">
        <input type="number" id="colsInput" class="swal2-input" placeholder="Number of columns" value="${cols}">
    `,
    focusConfirm: false,
    preConfirm: () => {
        const rows = document.getElementById('rowsInput').value;
        const cols = document.getElementById('colsInput').value;
        if (!rows || !cols) {
        Swal.showValidationMessage('Please enter both number of rows and columns');
        return false;
        }
        return { rows: parseInt(rows), cols: parseInt(cols) };
    }
    }).then((result) => {
    if (result.isConfirmed) {
        const { rows, cols } = result.value;
        console.log(`New grid size: ${rows} rows x ${cols} columns`);
        // currentRows = rows;
        // currentCols = cols;
        document.getElementById('rows').value = rows;
        document.getElementById('cols').value = cols;
        createGrid();
    }; 
    }
    );
}  

function toggleManualPlacementTools() {
    const tools = document.getElementById('manual_placement_tools');
    const toggleLink = document.getElementById('view_hide_manual_placement_tools');
    if (tools.style.display === 'none') {
        tools.style.display = 'flex';
        toggleLink.textContent = 'Hide Manual Placement Tools';
    } else {
        tools.style.display = 'none';
        toggleLink.textContent = 'Show Manual Placement Tools';
    }
}

toggleManualPlacementTools(); // Hide manual placement tools by default

function toggleGridCellLabels() {
    const labels = document.querySelectorAll('.cell-label');
    const toggleLink = document.getElementById('view_hide_grid_cell_labels');
    labels.forEach(label => {
            if (label.style.display === 'none') {
                label.style.display = 'block';
                    // toggleLink.style.background = 'white';

            } else {
                label.style.display = 'none';
                    
                // set all grid-cell.has-image background to transparent to make the grid cells with images look better when the labels are hidden
                const cellsWithImages = document.querySelectorAll('.grid-cell.has-image');
                cellsWithImages.forEach(cell => {
                    cell.style.background = 'transparent';
                });

            }

        }
    );
    if (toggleLink.textContent === 'Hide Grid Cell Labels') {
        toggleLink.textContent = 'Show Grid Cell Labels';
    } else {          
        toggleLink.textContent = 'Hide Grid Cell Labels';
    }
}
function showLoadSPICENetlistDialog() {
    const file = event.target.files[0];
    if (!file) {
        console.error("No file selected");
        return;
    };
    console.log("Selected file:", file);
    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        console.log("SPICE Netlist Content:", content);
        spiceInput = content;

        Swal.fire({
            title: "Loaded SPICE Netlist successfully!",
            icon: "success",
            // draggable: true
            // html: `SPICE File Content: <br/> <br/> ${content.replace(/\n/g, '<br/>')}`,

            // show SPICE netlist content in a scrollable div with max height of 300px, and set the font to monospace for better readability (with border and padding)
            html: `<div style="max-height: 300px; overflow-y: auto; font-family: monospace; text-align: left; border: 1px solid #ccc; padding: 10px;">${content.replace(/\n/g, '<br/>')}</div>`,
        });
        spiceFileInput.value = '';

    };
    reader.onerror = function(e) {
        console.error("Error reading file:", e);
    };
    reader.readAsText(file);

    // set src of imgStatusLoadSPICENetlist to on1.png to indicate successful loading of SPICE netlist
    document.getElementById('imgStatusLoadSPICENetlist').src = "static/on1.png";


}

let spiceInput = null;
document.getElementById('spiceFileInput').addEventListener('change', function(event) {
    showLoadSPICENetlistDialog();
});

function drawComponents(components) {
// draw the components on the grid canvas based on the generated placement data from the server
    // components is a dictionary with key as component name, and value as an array of [row, col, orientation, type]
    // for example: {"m1": [10, 2, 1, "nmos_normal"], "m2": [3, 8, 0, "pmos_diode"], ...}
    // orientation is 0 for normal     orientation, and 1 for flipped orientation (flipped horizontally)
    // type can be "nmos_normal", "nmos_diode", "pmos_normal", "pmos_diode", or "cap_vertical" 

    for (const [compName, compData] of Object.entries(components)) {
        console.log(`Drawing component ${compName} at row/col = (${compData[0]}, ${compData[1]}) with orientation ${compData[2]} and type ${compData[3]}`);
        const [col, row, orientation, type] = compData;
        let imageUrl = "static/port.png";
        if (type === "cap_vertical") {
            imageUrl = "static/cap.png";
        } else if (type == "resistor") {
            imageUrl = orientation === 1 ? "static/two-terminals/resistor_1.png" : "static/two-terminals/resistor.png";
        } else if (type === "nmos_normal") {
            imageUrl = orientation === 1 ? "static/nmos_normal_gate_left.png" : "static/nmos_normal_gate_right.png";
        } else if (type === "nmos_diode") {
            imageUrl = orientation === 1 ? "static/nmos_normal_gate_left.png" : "static/nmos_normal_gate_right.png";
        } else if (type === "pmos_normal") {
            imageUrl = orientation === 1 ? "static/pmos_normal_gate_left.png" : "static/pmos_normal_gate_right.png";
        } else if (type === "pmos_diode") {
            imageUrl = orientation === 1 ? "static/pmos_normal_gate_left.png" : "static/pmos_normal_gate_right.png";
        } 
        

        else if (type == "pnp_normal") {
            imageUrl = orientation === 1 ? "static/bjt/pnp_normal_base_left.png" : "static/bjt/pnp_normal_base_right.png";
        } else if (type === "pnp_diode") {
            imageUrl = orientation === 1 ? "static/bjt/pnp_diode_base_left.png" : "static/bjt/pnp_diode_base_right.png";
        }
        else if (type == "npn_normal") {
            imageUrl = orientation === 1 ? "static/bjt/npn_normal_base_left.png" : "static/bjt/npn_normal_base_right.png";
        } else if (type === "npn_diode") {
            imageUrl = orientation === 1 ? "static/bjt/npn_diode_base_left.png" : "static/bjt/npn_diode_base_right.png";
        }
        
        else if (type == "gnd")
        {
            imageUrl = "static/gnd.png";
        }


        // Find the cell
        const cell = document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
        if (!cell) {
            console.warn(`Cell not found for component ${compName} at (${row}, ${col})`);
            continue;
        }
        // remember component association on the cell
        try { cell.dataset.compName = compName; } catch (e) {}

        // Add image to cell
        addImageToCell(cell, imageUrl);
        // Add component name label
        if (compName.startsWith("terminal_gnd!")) {
            updated_compName = "";

        }
        else if (compName.startsWith("terminal_")) {
            // For terminals, we only show the port name without the "terminal_" prefix
            updated_compName = compName.replace("terminal_", "");
        }
        else {
            updated_compName = compName;
        }
        

        const label = document.createElement('div');
        label.className = 'cell-label-component-name';
        label.textContent = updated_compName;
        // remove existing component label if any
        const existingLabel = cell.querySelector('.cell-label-component-name');
        if (existingLabel) existingLabel.remove();
        cell.appendChild(label);

    };

}

function updateMessage(message) {
const infoDiv = document.getElementById('info');
infoDiv.innerHTML = message;
}

// derive image url for component type+orientation (same logic as drawComponents)
function getImageUrlForComponentType(type, orientation) {
    let imageUrl = "static/port.png";
    if (type === "cap_vertical") {
        imageUrl = "static/cap.png";
    } else if (type == "resistor") {
        imageUrl = orientation === 1 ? "static/two-terminals/resistor_1.png" : "static/two-terminals/resistor.png";
    } else if (type === "nmos_normal") {
        imageUrl = orientation === 1 ? "static/nmos_normal_gate_left.png" : "static/nmos_normal_gate_right.png";
    } else if (type === "nmos_diode") {
        imageUrl = orientation === 1 ? "static/nmos_normal_gate_left.png" : "static/nmos_normal_gate_right.png";
    } else if (type === "pmos_normal") {
        imageUrl = orientation === 1 ? "static/pmos_normal_gate_left.png" : "static/pmos_normal_gate_right.png";
    } else if (type === "pmos_diode") {
        imageUrl = orientation === 1 ? "static/pmos_normal_gate_left.png" : "static/pmos_normal_gate_right.png";
    } else if (type == "pnp_normal") {
        imageUrl = orientation === 1 ? "static/bjt/pnp_normal_base_left.png" : "static/bjt/pnp_normal_base_right.png";
    } else if (type === "pnp_diode") {
        imageUrl = orientation === 1 ? "static/bjt/pnp_diode_base_left.png" : "static/bjt/pnp_diode_base_right.png";
    } else if (type == "npn_normal") {
        imageUrl = orientation === 1 ? "static/bjt/npn_normal_base_left.png" : "static/bjt/npn_normal_base_right.png";
    } else if (type == "npn_diode") {
        imageUrl = orientation === 1 ? "static/bjt/npn_diode_base_left.png" : "static/bjt/npn_diode_base_right.png";
    } else if (type == "gnd") {
        imageUrl = "static/gnd.png";
    }
    return imageUrl;
}

function updateCellImageForComponent(cell, compName, compData) {
    if (!cell || !compData) return;
    const orientation = compData[2] || 0;
    const type = compData[3] || '';
    const imageUrl = getImageUrlForComponentType(type, orientation);

    // replace image
    addImageToCell(cell, imageUrl);

    // ensure component label
    const labelText = (compName.startsWith('terminal_') ? compName.replace('terminal_', '') : compName);
    const existingLabel = cell.querySelector('.cell-label-component-name');
    if (existingLabel) {
        existingLabel.textContent = labelText;
    } else {
        const label = document.createElement('div');
        label.className = 'cell-label-component-name';
        label.textContent = labelText;
        cell.appendChild(label);
    }
}

function routingToCanvasCoordinates(x, y, canvasHeight) {
    // Input routing coordinates: origin at bottom-left, 100 units per grid cell
    // Canvas coordinates: origin at top-left, 50 px per grid cell
    const scale = 0.5;
    return {
        x: x * scale,
        y: canvasHeight - y * scale,
    };
}

function sanitizeNetName(netName) {
    return String(netName).replace(/[^a-zA-Z0-9_-]/g, '_');
}

function createRoutingLayer(netName, width, height, zIndex) {
    const routingLayers = document.getElementById('routingLayers');
    const layerCanvas = document.createElement('canvas');
    layerCanvas.className = 'routing-layer-canvas';
    layerCanvas.id = `routingLayer_${sanitizeNetName(netName)}`;
    layerCanvas.dataset.netName = netName;
    layerCanvas.width = width;
    layerCanvas.height = height;
    layerCanvas.style.zIndex = String(zIndex);
    routingLayers.appendChild(layerCanvas);
    return layerCanvas;
}

function renderRoutingLayerToggles(layerDefinitions) {
    const routingLayerList = document.getElementById('routingLayerList');
    if (!routingLayerList) {
        return;
    }

    routingLayerList.innerHTML = '';

    layerDefinitions.forEach(({ netName, color, layerId }) => {
        const row = document.createElement('label');
        row.className = 'routing-layer-item';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;
        checkbox.dataset.layerId = layerId;
        checkbox.addEventListener('change', () => {
            const layerCanvas = document.getElementById(layerId);
            if (!layerCanvas) {
                return;
            }
            layerCanvas.style.display = checkbox.checked ? 'block' : 'none';
        });

        const colorChip = document.createElement('span');
        colorChip.className = 'routing-color-chip';
        colorChip.style.backgroundColor = color;

        const labelText = document.createElement('span');
        labelText.textContent = netName;

        row.appendChild(checkbox);
        row.appendChild(colorChip);
        row.appendChild(labelText);
        routingLayerList.appendChild(row);
    });
}

function toggleAllRoutingLayers(isEnabled) {
    const checkboxes = document.querySelectorAll('#routingLayerList input[type="checkbox"]');
    checkboxes.forEach((checkbox) => {
        checkbox.checked = isEnabled;
        const layerId = checkbox.dataset.layerId;
        if (!layerId) {
            return;
        }
        const layerCanvas = document.getElementById(layerId);
        if (!layerCanvas) {
            return;
        }
        layerCanvas.style.display = isEnabled ? 'block' : 'none';
    });
}

function shuffle(array) {
    let currentIndex = array.length;

    // While there remain elements to shuffle...
    while (currentIndex != 0) {

        // Pick a remaining element...
        let randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex--;

        // And swap it with the current element.
        [array[currentIndex], array[randomIndex]] = [
        array[randomIndex], array[currentIndex]];
    }
}

function drawRoutedNets(nets, intersectionPoints) {
// draw the routed nets on the grid canvas based on the generated routing data from the server
// example format of nets: 
// {"ibias":[[300,270],[300,279],[847,250],[992,250],[596,250],[585,250],[981,250],[741,250],[730,250],[300,256],[886,250],[490,250],[479,250],[875,250],[624,250],[228,250],[239,250],[373,250],[798,250],[809,250],[954,250],[558,250],[547,250],[943,250],[703,250],[692,250],[681,250],[307,250],[452,250],[441,250],[837,250],[586,250],[190,250],[296,250],[335,250],[760,250],[916,250],[509,250],[5２０,２５０],[９０５,２５０],[６６５,２５０],[６５４,２５０],[６４３,２５０],[８９４,２５０].[４０３,２５０].[３９２,２５０].[２４７,２５０].[５４８,２５０].[１５２,２５０].[２５８,２５０].[２６９,２５０].[３００,２６５].[２７９,３００].[７９０,２５０].[９７３,２５０].[７２２,２５０].[３２６,
// each key in nets is a net name, and the value is an array of coordinate points that form the routed path for that net. Each coordinate point is an array of [x,
// we may draw points  to represent routed wires,
// we may also draw intersection points for better visualization

    if (!nets || typeof nets !== 'object') {
        console.error("Invalid nets data:", nets);
        return;
    }


//  const colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe'];
//  const colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe'];
// hex color of orange, light blue, pink, light green, gray, light purple, light orange, light gray, light yellow, light cyan (dark version of the above colors for better visibility on white background)
    //const colors =  ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c',  '#008080', '#9a6324', '#800000',  '#808000',  '#000075', "#4B4B4B"];
//  ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080', '#ffffff', '#000000'];
    
colors = ["#F55A07", "#410252", "#A41600", "#E60DC1", "#004761",
    "#2F8900", "#945701", "#009478", "#F50A1F", "#F5BB00", 
    "#7701F5", "#D4C359", "#4C7DA2", "#937F6A", "#A85F5C",
    "#5C4C28", "#0E14DC", "#8AC944", "#876AD6", "#EEACC3",
    "#5C4C28", "#9CACDA",  "#000000", "#968fff", "#ff8f96"
];

shuffle(colors); // Shuffle colors to assign different colors for different nets each time
    // draw each net in different routingCanvas layer to avoid overlapping of different nets, and we can also toggle the visibility of each net by toggling the visibility of the corresponding routingCanvas layer

    const routingLayers = document.getElementById('routingLayers');
    if (!routingLayers) {
        console.error("Routing layers container not found");
        return;
    }

    const canvasWidth = document.getElementById('gridCanvas').clientWidth;
    const canvasHeight = document.getElementById('gridCanvas').clientHeight;

    // Clear previous routing layers
    routingLayers.innerHTML = '';

    let colorIndex = 0;
    const layerDefinitions = [];
    // Iterate through each net (nets is an object with net names as keys)
    for (const [netName, coordinates] of Object.entries(nets)) {
        if (!Array.isArray(coordinates) || coordinates.length === 0) {
            console.warn(`Invalid coordinates for net ${netName}:`, coordinates);
            continue;
        }
        else {
            console.log(`Drawing net ${netName} with coordinates:`, coordinates);
        }

        const color = colors[colorIndex % colors.length];
        const layerCanvas = createRoutingLayer(netName, canvasWidth, canvasHeight, 10 + colorIndex);
        const ctx = layerCanvas.getContext('2d');

        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 0.25;
        
        // Draw lines connecting the coordinate points
    //  ctx.beginPath();
    //  coordinates.forEach(([x, y], idx) => {
    //      const p = routingToCanvasCoordinates(x, y);
    //      if (idx === 0) {
    //          ctx.moveTo(p.x, p.y);
    //      } else {
    //          ctx.lineTo(p.x, p.y);
    //      }
    //  });
    //  ctx.stroke();
        
        // Draw points at each coordinate to represent routed wires

        
        coordinates.forEach(([x, y]) => {
            const p = routingToCanvasCoordinates(x, y, canvasHeight);
            ctx.beginPath();
            ctx.arc(p.x, p.y, 0.9, 0, 2 * Math.PI);
            ctx.fill();
        });
        if (intersectionPoints && Array.isArray(intersectionPoints[netName])) {
            intersectionPoints[netName].forEach(([x, y]) => {
            console.log(`Drawing intersection point for net ${netName} at (${x}, ${y})`);
                const p = routingToCanvasCoordinates(x, y , canvasHeight);
                ctx.beginPath();
                ctx.fillStyle = color;
                ctx.arc(p.x, p.y, 3.0, 0, 2 * Math.PI);
                ctx.fill();
            });
        }
        layerDefinitions.push({
            netName,
            color,
            layerId: layerCanvas.id,
        });
        
        colorIndex++;
    //  break; // Remove this break statement to draw all nets, currently only drawing the first net for demonstration
    }

    renderRoutingLayerToggles(layerDefinitions);
}

function showGeneratePlacementDialog() {
    Swal.fire({
    title: "Do you want to keep the current placement and apply orientation constraints only?",
    text: "If you choose 'Yes', the schematic will be generated based on the current placement with the applied orientation constraints. If you choose 'No, start with the new placement', the current placement will be cleared and the schematic will be generated with a new placement based on the specified constraints.",
    showDenyButton: true,
    showCancelButton: true,
    icon: "warning",
    confirmButtonText: "Yes",
    confirmButtonColor: "#03AED2",
    denyButtonText: `No, start with the new placement`,
    denyButtonColor: "#D12052",

    }).then((result) => {
    /* Read more about isConfirmed, isDenied below */
    if (result.isConfirmed) {
        updateMessage("Keeping the current placement. You can still generate placement later by clicking the 'Generate Schematic' button.");
        generatePlacement();
    }
    else if (result.isDenied) {
        updateMessage("Starting with the new placement.");
        componentPlacementData = {}; // reset the current component placement data
        generatePlacement();
    }
    });
}
function generatePlacement() {
// Placeholder function for generating placement based on constraints
// alert('Generating placement based on specified constraints...');
// alert('SPICE content: \n' + spiceInput);

// send POST request to /schengen endpoint with the SPICE netlist content and the constraints specified in the right panel (heuristic, path-based, subcircuit-based, LLM-generated, and user-defined)
clearGrid();

// get constraints from the right panel
const selectedPathBasedConstraints = [];
document.querySelectorAll('#selPathbasedConstraints input[type="checkbox"]:checked').forEach(checkbox => {
    selectedPathBasedConstraints.push(checkbox.value);
}); 
document.querySelectorAll('#selPathbasedConstraints input[type="radio"]:checked').forEach(checkbox => {
    selectedPathBasedConstraints.push(checkbox.value);
}); 

const constraints = {
    subcircuit_info: document.getElementById('txtSubcircuitInfo').value,
    partitioning_info: document.getElementById('txtPartitioningInfo').value,
    llm_generated: document.getElementById('txtLLMGeneratedConstraints').value,
    user_defined: document.getElementById('txtUserConstraints').value,
    orientation_constraints: document.getElementById('txtOrientationData').value,
    path_based_constraints: selectedPathBasedConstraints,
    // get terminals from textbox with id="terminalPorts" and seperate them by "," and save them as a list of strings in the constraints configuration file
    terminals: document.getElementById('txtTerminalPorts').value.split(',').map(s => s.trim()).filter(s => s.length > 0),
    component_placement_data: componentPlacementData
};



console.log("Constraints:", constraints);
updateMessage("Generating schematic... Please wait. This may take a few seconds/minutes. Please do not close or refresh the page while the schematic is being generated. Refer to the console for more details.");

// send request and display response in a SweetAlert2 modal
fetch('/schengen', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'            },
    body: JSON.stringify({
        netlist: spiceInput,
        constraints: constraints,
    })
})
.then(response => {
    return response.json();
} )
.then(data => {
    // show error message only if data contains response code other than 200
    updateMessage("Done generating schematic.");
    console.log("Response from server:", data);
    if (data["status"] !== 200) {
        updateMessage("Error generating schematic: " + data["message"]);
        Swal.fire({
            title: "Error Generating Schematic",
            icon: "error",
            html: `${data["message"]}`,
        });
        return;
    }

    Swal.fire({
        title: "Schematic Generated Successfully!",
        icon: "success",
        // html: `Generated Schematic Data: <br/> <br/> ${JSON.stringify(data).replace(/\n/g, '<br/>')}`,

        // print unrouted nets and connected components
        // print unrouted nets in the response data, which is a dictionary with net names as keys and the connected components as values
        html: `Unrouted Nets: <br/> <br/> ${JSON.stringify(data["data"]["unrouted_nets_data"]).replace(/\n/g, '<br/>')}`,
        
    });



    // an example of data
    // {"data":{"component_placement_data":{"c1":[11,4,0,"cap_vertical"],"c2":[9,4,0,"cap_vertical"],"m1":[10,2,1,"nmos_normal"],"m10":[8,8,1,"pmos_normal"],"m11":[2,2,0,"nmos_diode"],"m12":[10,6,1,"pmos_diode"],"m2":[3,8,0,"pmos_diode"],"m3":[5,6,0,"pmos_normal"],"m4":[5,8,1,"pmos_normal"],"m5":[4,2,1,"nmos_normal"],"m6":[3,4,1,"nmos_normal"],"m7":[5,4,0,"nmos_normal"],"m8":[8,2,1,"nmos_normal"],"m9":[8,6,1,"pmos_normal"],"terminal_gnd!c2":[9,3,1,"gnd"],"terminal_gnd!m1":[10,1,1,"gnd"],"terminal_gnd!m11":[2,1,1,"gnd"],"terminal_gnd!m5":[4,1,1,"gnd"],"terminal_gnd!m8":[8,1,1,"gnd"],"terminal_ibias":[1,2,1,"port"],"terminal_in1":[1,4,1,"port"],"terminal_in2":[7,4,1,"port"],"terminal_out":[13,4,1,"port"],"terminal_vdd!":[11,9,1,"port"]},"routing_cost":0},"message":"Input SPICE Netlist & Constraints received successfully!","status":200}

    // get component_placement_data and draw components into the gird canvas
    componentPlacementData = data["data"]["component_placement_data"];
    latestSchengenResultPath = data["data"]["schengen_result_path"] || latestSchengenResultPath;
    drawComponents(componentPlacementData);
    
    // get routed points and draw the routing on the grid canvas 
    routedNetsData = data["data"]["routed_nets"];
    intersectionPointsData = data["data"]["intersection_points"];


    if (routedNetsData && typeof routedNetsData === 'object') {
        drawRoutedNets(routedNetsData, intersectionPointsData);
    } else {
        console.warn("No routed nets data available or invalid format:", routedNetsData);
    }

})
.catch(error => {
    console.error("Error:", error);
    Swal.fire({
        title: "Error Generating Schematic",
        icon: "error",
        text: "~An error occurred while generating the schematic. Please try again.",
    });
});
}

// save current constraints configuration to file when user clicks the "Save Constraint Settings" button, 
// and load the saved constraints configuration from file when user clicks the "Load Constraints" button. 
// This allows users to easily save and load their constraint configurations without needing to manually copy and paste the constraints data.
// Also open the File Explorer dialog to let user choose the location and name of the saved file when saving constraints, and to choose the file to load when loading constraints.
function saveConstraints() {

    // get selected path-based constraint items
    const selectedPathBasedConstraints = [];
    document.querySelectorAll('#selPathbasedConstraints input[type="checkbox"]:checked').forEach(checkbox => {
        selectedPathBasedConstraints.push(checkbox.value);
    });
    document.querySelectorAll('#selPathbasedConstraints input[type="radio"]:checked').forEach(checkbox => {
        selectedPathBasedConstraints.push(checkbox.value);
    });
    // get terminals from textbox with id="terminalPorts" and seperate them by "," and save them as a list of strings in the constraints configuration file
    terminalsText = document.getElementById('txtTerminalPorts').value;
    const terminals = terminalsText.split(',').map(s => s.trim()).filter(s => s.length > 0);


    const constraints = {

        subcircuit_info: document.getElementById('txtSubcircuitInfo').value,
        partitioning_info: document.getElementById('txtPartitioningInfo').value,
        llm_generated: document.getElementById('txtLLMGeneratedConstraints').value,
        user_defined: document.getElementById('txtUserConstraints').value,
        orientation_constraints: document.getElementById('txtOrientationData').value,
        path_based_constraints: selectedPathBasedConstraints,
        terminals: terminals
    };
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(constraints, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "constraints_config.json");
    document.body.appendChild(downloadAnchorNode); // required for firefox
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
        
}

// open file dialog to load constraints configuration from file, and update the constraints textareas with the loaded data when user clicks the "Load Constraints" button
function loadConstraints() {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';
    fileInput.onchange = (event) => {
        const file = event.target.files[0];
        if (!file) {
            console.error("No file selected");
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const constraints = JSON.parse(e.target.result);
                document.getElementById('txtSubcircuitInfo').value = constraints.subcircuit_info || "";
                document.getElementById('txtPartitioningInfo').value = constraints.partitioning_info || "";
                document.getElementById('txtLLMGeneratedConstraints').value = constraints.llm_generated || "";
                document.getElementById('txtUserConstraints').value = constraints.user_defined || "";
                document.getElementById('txtOrientationData').value = constraints.orientation_constraints || "";
                document.getElementById('txtTerminalPorts').value = constraints.terminals ? constraints.terminals.join(',') : "";

                    // update path-based constraints checkboxes
                if (Array.isArray(constraints.path_based_constraints)) {
                    document.querySelectorAll('#selPathbasedConstraints input[type="checkbox"]').forEach(checkbox => {
                        checkbox.checked = constraints.path_based_constraints.includes(checkbox.value);
                    });

                    document.querySelectorAll('#selPathbasedConstraints input[type="radio"]').forEach(checkbox => {
                        checkbox.checked = constraints.path_based_constraints.includes(checkbox.value);
                    });

                }


                Swal.fire({
                    title: "Constraints Loaded Successfully!",
                    icon: "success",
                    // html: `Loaded Constraints: <br/> <br/> ${JSON.stringify(constraints).replace(/\n/g, '<br/>')}`,
                    // html: `Loaded Constraints successfully!`,
                });


                // set src of imgStatusLoadConstraints to on1.png to indicate successful loading of constraints configuration file
                document.getElementById('imgStatusLoadConstraints').src = "static/on1.png";

            } catch (error) {
                console.error("Error parsing JSON:", error);
                Swal.fire({
                    title: "Error Loading Constraints",
                    icon: "error",
                    text: "Failed to parse the selected file. Please make sure it's a valid JSON file with the correct format.",
                });
            }
        };
        reader.onerror = (e) => {
            console.error("Error reading file:", e);
            Swal.fire({
                title: "Error Loading Constraints",
                icon: "error",
                text: "An error occurred while reading the file. Please try again.",
            });
        };
        reader.readAsText(file);
    };
    fileInput.click();

}

// set number of columns based on current window width when the page loads, and update the grid size accordingly. Assuming each grid cell is 50px wide, we can calculate the number of columns that can fit in the current window width, and set that as the value of the columns input field, and then call the changeGridSize function to update the grid.
function updateGridSizeBasedOnWindowWidth() {
    const cellSize = 50; // Assuming each grid cell is 50px wide
    // const cols = Math.floor(window.innerWidth / cellSize);

    // subtract the with of the right panel from the page width to get the available width for the grid, and then calculate the number of columns that can fit in the available width. 
    const rightPanelWidth = document.getElementById('rightPanel').offsetWidth + 50*2; // add some margin
    const availableWidth = window.innerWidth - rightPanelWidth;
    const cols = Math.floor(availableWidth / cellSize);

    document.getElementById('cols').value = cols;
    // changeGridSize();
    createGrid();
}

function toggleGridCellBorders() {
    const cells = document.querySelectorAll('.grid-cell');
    cells.forEach(cell => {
        if (cell.classList.contains('has-image')) {
            // cell.style.border = '1px solid #ccc';
                cell.style.border = 'none';
        } else {                        
            cell.style.border = 'none';
            cell.style.display = cell.style.display === 'none' ? 'block' : 'none';
            const gridCanvas = document.getElementById('gridCanvas');
            if (gridCanvas) {
                gridCanvas.style.backgroundSize = cell.style.display === 'none' ? 'cover' : '50px 50px';
            }
        }
    });
    console.log("Toggled grid cell borders for better visualization of grid layout and routing canvas");
}

// add function load generated placement and routing results from given upload JSON file, and draw the components and routed nets on the grid canvas accordingly.
function loadPlacementAndRoutingFromFile(event) {
    // open File select dialog to let user choose the JSON file that contains the generated placement and routing data, and then read the file and parse the JSON data, and draw the components and routed nets on the grid canvas based on the parsed data. The expected format of the JSON file is: {"component_placement_data": {"comp1": [row, col, orientation, type], "comp2": [row, col, orientation, type], ...}, "routed_nets": {"net1": [[x1, y1], [x2, y2], ...], "net2": [[x1, y1], [x2, y2], ...], ...}}
    

    const file = event.target.files[0];
    if (!file) {
        console.error("No file selected");
        return;
    };
    console.log("Selected file:", file);
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            console.log("Loaded Placement and Routing Data:", data);
            componentPlacementData = data["component_placement_data"];
            routedNetsData = data["routed_nets"];
            intersectionPointsData = data["intersection_points"];

            // set netlist input to the loaded SPICE netlist if it exists in the loaded data
            if (data["netlist"]) {
                spiceInput = data["netlist"];
                document.getElementById('spiceFileInput').value = ''; // clear the file input value
                // set src of imgStatusLoadSPICENetlist to on1.png to indicate successful loading of SPICE netlist
                document.getElementById('imgStatusLoadSPICENetlist').src = "static/on1.png";

            }   
            
            if (data["terminals"]) {
                document.getElementById('txtTerminalPorts').value = data["terminals"].join(',');
                
            }
            // clear existing grid and routing layers before drawing the new placement and routing data
            createGrid();

            drawComponents(componentPlacementData);
            drawRoutedNets(routedNetsData, intersectionPointsData );
            Swal.fire({
                title: "Placement and Routing Loaded Successfully!",
                icon: "success",
                // html: `Loaded Placement and Routing Data: <br/> <br/> ${JSON.stringify(data).replace(/\n/g, '<br/>')}`,
                html: `Loaded Placement and Routing successfully!. Unrouted Nets: <br/> <br/> ${JSON.stringify(data["unrouted_nets_data"]).replace(/\n/g, '<br/>')}`,
            });
        } catch (error) {
            console.error("Error parsing JSON:", error);
            Swal.fire({
                title: "Error Loading Placement and Routing",
                icon: "error",
                text: "Failed to parse the selected file. Please make sure it's a valid JSON file with the correct format.",
            });
        }
    };
    reader.onerror = function(e) {
        console.error("Error reading file:", e);
        Swal.fire({
            title: "Error Loading Placement and Routing",
            icon: "error",
            text: "An error occurred while reading the file. Please try again.",
        });
    };
    reader.readAsText(file);
}   

// set btn click handler for loading placement and routing data from file
document.getElementById('loadSchematicBtn').addEventListener('click', () => {
    document.getElementById('placementRoutingFileInput').click();
});

// set change event handler for the file input to load placement and routing data from the selected file
document.getElementById('placementRoutingFileInput').addEventListener('change', loadPlacementAndRoutingFromFile);   

// set btn click handlers
document.getElementById('btnOpenSPICEFile').addEventListener('click', () => {
    document.getElementById('spiceFileInput').click();
});
document.getElementById('btnSaveConstraints').addEventListener('click', saveConstraints);
document.getElementById('btnLoadConstraints').addEventListener('click', loadConstraints);
document.getElementById('btnGenerateSchematic').addEventListener('click', showGeneratePlacementDialog);
document.getElementById('btnHideGridCells').addEventListener('click', toggleGridCellBorders);
document.getElementById('saveConstraintsBtn').addEventListener('click', saveConstraints);
document.getElementById('loadConstraintsBtn').addEventListener('click', loadConstraints);
document.getElementById('btnExportSchematic').addEventListener('click', showExportFormatDialog);


window.addEventListener('load', () => {
    //updateGridSizeBasedOnWindowWidth();
    
});

// update when window is resized
window.addEventListener('resize', () => {
    // updateGridSizeBasedOnWindowWidth();
}); 


// toggle manual placement tools and grid cell labels visibility using  hotkeys: Ctrl + B for manual placement tools, Ctrl + G for grid cell labels
document.addEventListener('keydown', (e) => {
    // handle left/right arrows: if a component cell is selected, change orientation; otherwise scroll canvas
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        const selectedCell = document.querySelector('.grid-cell.selected');
        const canvasColumn = document.getElementById('canvasColumn');
        if (selectedCell && selectedCell.dataset && selectedCell.dataset.compName) {
            e.preventDefault();
            const compName = selectedCell.dataset.compName;
            if (componentPlacementData && componentPlacementData[compName]) {
                const data = componentPlacementData[compName];
                let orientation = parseInt(data[2] || 0, 10);
                if (e.key === 'ArrowLeft') {
                    orientation = (orientation - 1 + 2) % 2;
                } else {
                    orientation = (orientation + 1) % 2;
                }
                data[2] = orientation;
                componentPlacementData[compName] = data;
                updateCellImageForComponent(selectedCell, compName, data);
            }
        } else {
            // scroll the canvas horizontally when no component selected
            e.preventDefault();
            const delta = e.key === 'ArrowLeft' ? -120 : 120;
            if (canvasColumn) {
                canvasColumn.scrollLeft += delta;
            } else {
                window.scrollBy({ left: delta, behavior: 'smooth' });
            }
        }
        return;
    }
    if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        toggleManualPlacementTools();
    }
    if (e.ctrlKey && e.key === 'w') {
        e.preventDefault();
        toggleGridCellLabels();
    }
    if (e.ctrlKey && e.key == 'g') {
        e.preventDefault();
        showGeneratePlacementDialog();

    }
    if (e.ctrlKey && e.key == 'o') {
        e.preventDefault();
        document.getElementById('spiceFileInput').click();

    }

    if (e.ctrlKey && e.key == 't') {
        // for testing purpose, draw some points on the routing canvas at routing coordinates (0,0) and (300,400) to verify the coordinate transformation 
        // and the drawing functionality on the routing canvas. The point at (0,0) should be at the bottom-left corner of the grid canvas, 
        // and the point at (300,400) should be 3 grid cells to the right and 4 grid cells up from the bottom-left corner.

        e.preventDefault();

        const routingLayers = document.getElementById('routingLayers');
        if (!routingLayers) {
            console.error("Routing layers container not found");
            return;
        }

        routingLayers.innerHTML = '';

        const canvasWidth = document.getElementById('gridCanvas').clientWidth;
        const canvasHeight = document.getElementById('gridCanvas').clientHeight;
        const testCanvas = createRoutingLayer('test_layer', canvasWidth, canvasHeight, 99);
        const ctx = testCanvas.getContext('2d');

        const color = '#e6194b';
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 2;

        const p1 = routingToCanvasCoordinates(0, 0, canvasHeight);
        const p2 = routingToCanvasCoordinates(300, 400, canvasHeight);

        ctx.beginPath();
        ctx.arc(p1.x, p1.y, 2, 0, 2 * Math.PI);
        ctx.arc(p2.x, p2.y, 2, 0, 2 * Math.PI);
        ctx.fill();

        renderRoutingLayerToggles([
            { netName: 'test_layer', color, layerId: testCanvas.id },
        ]);

        console.log("Test drawing on routing canvas at routing coords (0,0) and (300,400)");
    }

    if (e.ctrlKey && e.key == 'q') {
        // toggle grid cell borders visibility for better visualization of the grid layout and the routing canvas.
        //  This is useful for debugging the placement and routing results, as well as for understanding the grid structure 
        // and how the components are placed and routed on the grid. When toggled on, it will show the borders of the grid cells, 
        // which can help to see how the components are aligned with the grid and how the routing paths navigate through the grid. 
        // When toggled off, it will hide the borders for a cleaner view of the schematic.

        e.preventDefault();

        const cells = document.querySelectorAll('.grid-cell');
        cells.forEach(cell => {
            if (cell.classList.contains('has-image')) {
                // cell.style.border = '1px solid #ccc';
                    cell.style.border = 'none';
            } else {                        
                cell.style.border = 'none';
                cell.style.display = cell.style.display === 'none' ? 'block' : 'none';
                const gridCanvas = document.getElementById('gridCanvas');
                if (gridCanvas) {
                    gridCanvas.style.backgroundSize = cell.style.display === 'none' ? 'cover' : '50px 50px';
                }
            }
        });
        console.log("Toggled grid cell borders for better visualization of grid layout and routing canvas");
    }

    if (e.ctrlKey && e.key == 's'){
        e.preventDefault();
        saveConstraints();
    }
    
    if (e.ctrlKey && e.key == 'p') {
        e.preventDefault();
        loadConstraints();
    }

    if (e.ctrlKey && e.key == 'r') {
        e.preventDefault();
        updateGridSizeBasedOnWindowWidth();
    }
    if (e.ctrlKey && e.key == 'd') {
        e.preventDefault();
        componentPlacementData = {};
        // show alertbox to inform that previous placement data has been cleared
        Swal.fire({
            title: "Component Placement Data Cleared",
            icon: "info",
            text: "Previous component placement data has been cleared. schengen will perform P+R together when clicking `Generate Schematic`.",
        });
    }
});


// toggle opposite checked value for sel_P3, and sel_P3_1
document.getElementById('sel_P3').addEventListener('change', (e) => {
    document.getElementById('sel_P3_1').checked = !e.target.checked;
});



function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

function showExportFormatDialog() {
    Swal.fire({
        title: 'Select export format',
        text: 'Choose the file type to save.',
        showCancelButton: true,
        confirmButtonText: '.PNG',
        cancelButtonText: '.ASC (LTspice)',
        showDenyButton: false,
        reverseButtons: true,
    }).then((result) => {
        if (result.isConfirmed) {
            exportSchematicAsPNG();
            return;
        }

        if (result.dismiss === Swal.DismissReason.cancel) {
            exportLtspiceSchematic();
        }
    });
}

async function exportLtspiceSchematic() {
    try {
        const response = await fetch('/export_ltspice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                schengen_result_path: latestSchengenResultPath,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Failed to export LTspice file.');
        }

        const blob = await response.blob();
        const now = new Date();
        const timestamp = now.toISOString().replace(/[:.]/g, '-');
        downloadBlob(blob, `schematic_${timestamp}.asc`);
    } catch (error) {
        console.error('Error exporting LTspice schematic:', error);
        Swal.fire({
            title: 'Export Failed',
            icon: 'error',
            text: error.message || 'Unable to export LTspice schematic.',
        });
    }
}



// Export the composed schematic (combine routing canvases + grid images + labels) to a PNG file
async function exportSchematicAsPNG() {
    const gridCanvasDiv = document.getElementById('gridCanvas');
    const routingLayers = document.getElementById('routingLayers');
    if (!gridCanvasDiv) {
        console.error('Grid canvas not found');
        return;
    }

    // Save previous styles to restore later (hide only cell coordinates, keep component names)
    const cellCoordLabels = Array.from(document.querySelectorAll('.cell-label'));
    const prevCoordLabelDisplays = cellCoordLabels.map(el => el.style.display || '');
    cellCoordLabels.forEach(el => el.style.display = 'none');

    const cellElems = Array.from(document.querySelectorAll('.grid-cell'));
    const prevCellBorders = cellElems.map(el => el.style.border || '');
    cellElems.forEach(el => el.style.border = 'none');

    const prevBackgroundImage = gridCanvasDiv.style.backgroundImage || '';
    gridCanvasDiv.style.backgroundImage = 'none';

    // Determine export dimensions
    const exportWidth = Math.max(1, Math.round(gridCanvasDiv.clientWidth));
    const exportHeight = Math.max(1, Math.round(gridCanvasDiv.clientHeight));

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = exportWidth;
    exportCanvas.height = exportHeight;
    const ectx = exportCanvas.getContext('2d');

    // White background
    ectx.fillStyle = '#ffffff';
    ectx.fillRect(0, 0, exportWidth, exportHeight);

    // Draw routing canvases (sorted by zIndex)
    if (routingLayers) {
        const layerCanvases = Array.from(routingLayers.querySelectorAll('canvas.routing-layer-canvas'));
        layerCanvases.sort((a, b) => (parseInt(a.style.zIndex || 0) - parseInt(b.style.zIndex || 0)));
        layerCanvases.forEach(lc => {
            if (lc.style.display === 'none') return;
            try {
                ectx.drawImage(lc, 0, 0, lc.width, lc.height, 0, 0, exportWidth, exportHeight);
            } catch (err) {
                console.warn('Failed to draw routing layer', lc.id, err);
            }
        });
    }

    // Draw grid cell images (wait for images to load)
    const imgs = Array.from(gridCanvasDiv.querySelectorAll('.grid-cell img'));
    await Promise.all(imgs.map(img => new Promise(resolve => {
        if (img.complete) return resolve();
        img.addEventListener('load', () => resolve());
        img.addEventListener('error', () => resolve());
    })));

    imgs.forEach(img => {
        const cell = img.closest('.grid-cell');
        if (!cell) return;
        // position and size of the cell relative to gridCanvasDiv
        const left = parseFloat(cell.style.left) || cell.offsetLeft;
        const top = parseFloat(cell.style.top) || cell.offsetTop;
        const w = cell.clientWidth || (exportWidth / Math.max(1, currentCols));
        const h = cell.clientHeight || (exportHeight / Math.max(1, currentRows));
        try {
            ectx.drawImage(img, left, top, w, h);
        } catch (err) {
            console.warn('Failed to draw image in cell', cell, err);
        }
    });

    // Draw component name labels on canvas
    const componentLabels = Array.from(gridCanvasDiv.querySelectorAll('.cell-label-component-name'));
    componentLabels.forEach(label => {
        const cell = label.closest('.grid-cell');
        if (!cell) return;
        
        const left = parseFloat(cell.style.left) || cell.offsetLeft;
        const top = parseFloat(cell.style.top) || cell.offsetTop;
        const w = cell.clientWidth || (exportWidth / Math.max(1, currentCols));
        const h = cell.clientHeight || (exportHeight / Math.max(1, currentRows));
        
        // Draw text on canvas matching the CSS styling
        ectx.fillStyle = '#2600ff';  // Color from .cell-label-component-name CSS
        ectx.font = 'bold 12px sans-serif';
        ectx.textAlign = 'left';
        ectx.textBaseline = 'bottom';
        
        const labelText = label.textContent.trim();
        if (labelText) {
            // Position at left: 25px, bottom of cell (matching CSS positioning)
            ectx.fillText(labelText, left + 25, top + h - 2);
        }
    });

    // Create download
    const dataURL = exportCanvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = dataURL;
    const now = new Date();
    const timestamp = now.toISOString().replace(/[:.]/g, '-');
    a.download = `schematic_${timestamp}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();

    // Restore styles
    cellCoordLabels.forEach((el, i) => el.style.display = prevCoordLabelDisplays[i] || '');
    cellElems.forEach((el, i) => el.style.border = prevCellBorders[i] || '');
    gridCanvasDiv.style.backgroundImage = prevBackgroundImage;
}
