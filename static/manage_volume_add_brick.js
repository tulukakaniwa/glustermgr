var bricks = 0;
var brick_array = Array();

function add_element() {
    if (document.getElementById("brick_s_peer").value.length === 0) {
        alert("Please select a peer.");
        return
    }
    if (document.getElementById("brick_s_fspath").value.length === 0) {
        alert("Filesystem path must not be empty.");
        return
    }

    brick_array[bricks] = {
        peer: document.getElementById("brick_s_peer").value,
        fspath: document.getElementById("brick_s_fspath").value,
    };
    bricks++;
    document.getElementById("brick_s_fspath").value = "";
    display_array();
}

function del_element(element_id) {
    brick_array.splice(element_id, 1);
    display_array();
    bricks--;
}

function display_array() {
    document.getElementById("brick_list").innerHTML = "";
    var e = "";
    if (brick_array.length === 0) {
        e += "<p>(No bricks were added)</p>"
    } else {
        e += "<table class=\"all-left-align\"><tr><td>Peer Address</td><td>Filesystem Path</td><td>Delete</td></tr>";
        for (var counter = 0; counter < brick_array.length; counter++) {
            e += "<tr><td>" + brick_array[counter].peer + "</td><td>" + brick_array[counter].fspath + "</td><td style='text-align: center'><input type='button' onclick='del_element(" + counter + ")' value='-' alt='Delete brick'></td></tr>"
        }
        e += "</table>"
    }

    console.log(e);
    document.getElementById("brick_list").innerHTML = e;
}


function addDataToForm(form, data) {
    if (typeof form === 'string') {
        if (form[0] === '#') form = form.slice(1);
        form = document.getElementById(form);
    }

    var keys = Object.keys(data);
    var name;
    var value;
    var input;

    for (var i = 0; i < keys.length; i++) {
        name = keys[i];
        // removing the inputs with the name if already exists [overide]
        console.log(form);
        Array.prototype.forEach.call(form.elements, function (inpt) {
            if (inpt.name === name) {
                inpt.parentNode.removeChild(inpt);
            }
        });

        value = data[name];
        input = document.createElement('input');
        input.setAttribute('name', name);
        input.setAttribute('value', value);
        input.setAttribute('type', 'hidden');

        form.appendChild(input);
    }

    return form;
}

function replica_change_val() {
    brick_form = document.getElementById("create_brick_form");
    console.log("brick replica?", brick_form.replica.value);
    if (brick_form.arbiter_enable.checked) {
        brick_form.arbiter.removeAttribute("disabled");
    } else {
        console.log("disabled!")
        brick_form.arbiter.setAttribute("disabled", "");
        brick_form.arbiter.value = 0;

    }
}


window.onload = function () {
    brick_form = document.getElementById("create_brick_form");
    brick_form.onsubmit = function () {
        if (brick_array.length === 0) {
            alert("Please add at least one brick to create a new volume.");
            return false;
        }

        addDataToForm(document.getElementById('create_brick_form'), {
            bricks: JSON.stringify(brick_array)
        });
        return true;
    };
    brick_form.volume_name.value = "";
    brick_form.replica.value = 0;
    brick_form.arbiter.value = 0;

};
