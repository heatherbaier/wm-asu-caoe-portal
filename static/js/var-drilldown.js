var bs_config = {
    tooltips: {
        titleFontSize: 10,
        bodyFontSize: 9
    },
    maintainAspectRatio: false,
    legend: {
        display: false
    },
    title: {
        display: true,
        fontSize: 20
    },
    scales: {
        y: {
            beginAtZero: true
        },
        yAxes: [{
            ticks: {
                fontSize: 10
            }
        }],
        xAxes: [{
            ticks: {
                fontSize: 10
            }
        }]
    },
    annotation: {
        annotations: [
            {
                drawTime: "afterDatasetsDraw",
                type: "line",
                mode: "vertical",
                scaleID: "x-axis-0",
                value: 3000,
                borderWidth: 5,
                borderColor: "red",
                label: {
                    content: "TODAY",
                    enabled: true,
                    position: "top"
                }
            }
        ]
    }
}

function removeAllChildNodes(parent) {
    while (parent.firstChild) {
        parent.removeChild(parent.firstChild);
    }
}

function make_ale_plot(data, labels) {

    var plot1_div = document.getElementById("dd-plot1")
    plot1_div.style.height = "40%";

    var plot1_check = document.getElementById('plot1');

    console.log("plot1_check", plot1_check)

    if (plot1_check != null) {
        console.log("removing old canvas!!!")
        plot1_div.removeChild(plot1_check);
    }

    var plot1 = document.createElement('canvas');

    plot1.id = 'plot1';
    plot1_div.appendChild(plot1); // append the left chart to the left canvas

    var ctx1 = document.getElementById('plot1').getContext('2d');
    var myChart1 = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Change from average: ',
                data: data,
                fill: false,
                backgroundColor: 'rgba(70, 109, 29, 0.5)',
                borderColor: '#74b4ef',
                borderWidth: 5
            }]
        },
        options: bs_config
    });


}


function var_drilldown(elem) {

    console.log(elem.id)

    mymap.setView([23.6345, -95.5528], zoom_start = 6);

    // Make edits to elements that don't have to be deleted first
    document.getElementById("nav").style.width = "30%"
    document.getElementById("drill").style.display = "block"
    document.getElementById("drill").style.width = "45vh"
    // document.getElementById("data").style.width = "50%"
    // document.getElementById("drill-muni").style.fontSize = "35px"
    document.getElementById("drill-muni").innerHTML = elem.id.slice(5);
    // document.getElementById("radio-layers").style.marginRight = "28%"
    document.getElementById("fi-title").style.display = "block"
    document.getElementById("ale-title").style.fontWeight = "bold"
    document.getElementById("ale-title").style.display = "block"
    document.getElementById("drill-muni").style.fontWeight = "bold"
    document.getElementById("fi-title").style.fontWeight = "bold"
    document.getElementById("grid-container").style.width = "105vh"
    document.getElementById("mapid").style.width = "105vh"


    // Go through and remove anything that might be in the column already
    if (document.getElementById("plot1") != null) {
        document.getElementById("dd-plot1").removeChild(document.getElementById("plot1"))
    }

    var to_delete = ["unc_title", "unc_level", "unc_hr"]
    var to_delete_p = document.getElementById("drill");

    for (i = 0; i < to_delete.length; ++i) {
        if (document.getElementById(to_delete[i]) != null) {
            to_delete_p.removeChild(document.getElementById(to_delete[i]))
        }
    }


    // var container = document.querySelector("#ale-intervals");
    // removeAllChildNodes(container);

    fetch('/var_drilldown', {

        // When the data gets POSTed back to Flask, it'll be in JSON format
        headers: {
            'Content-Type': 'application/json'
        },

        // Send the data back as a POST request
        method: 'POST',

        // Here's where you construct the JSON
        body: JSON.stringify({
            "info_var": elem.id.slice(5)
        })

        // ...and then send it off
        }).then(function (response) {
            return response.text();
        }).then(function (text) {

            data = JSON.parse(text);

            console.log("done with fetch!!")

            document.getElementById("mig_perc").style.fontSize = "15px";
            document.getElementById("mig_perc").style.textAlign = "center";
            document.getElementById("mig_perc").innerHTML = elem.id.slice(5) + 
                                                            " is ranked <br><h1>" + data['var_rank'] + 
                                                            "</h1>in feature importance out of " + "206" + " variables,<br><h1>" + 
                                                            data['var_cat_rank'] + 
                                                            "</h1> among the " + data['num_cat_vars'] + " variables in its category," +
                                                            "and is considered <b>" + data['quant'] + "</b>"

            make_ale_plot(data['ale_values'], data['ale_labels'])   

            console.log(data['ale_values']);

            document.getElementById("myPopup").innerHTML = "For example, an effect of " + data['ale_values'][2].toLocaleString() + " between the interval " + data['ale_labels'][2] + " means that the prediction is different by about " + data['ale_values'][2].toLocaleString() + " migrants compared to the average prediction, if the value of " + elem.id.slice(5) + " is changed for all municipalities that fall within the interval."

        })


}