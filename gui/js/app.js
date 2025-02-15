
if (!customElements.get("x-flx")) {
    class Flexx extends HTMLDivElement {
        constructor() {
            super();
        }
    }

    customElements.define("x-flx", Flexx, { extends: 'div' })
}

/* dropdown upload */
function myFunction() {
    document.getElementById("myDropdown").classList.toggle("show");
}

// Close the dropdown if the user clicks outside of it
window.onclick = function (event) {
    if (!event.target.matches('.dropbtn i')) {
        var dropdowns = document.getElementsByClassName("dropdown-content");
        var i;
        for (i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}

let app = null;
let react = null;

function callback() {
    console.log("App loaded")
    app = document.getElementById("app")
    react = app.onreact

    react("app_update")

    let observer = new MutationObserver((mutations) => {
        react("app_update")
        let toggler = document.getElementById("fb-toggler");
        let content = document.querySelector(".filebrowserdiv");
        if (content && !toggler.classList.contains("activeC")) {
            content.style.display = "none";
        }
        if (toggler) {
            toggler.onclick = function() {
                toggler.classList.toggle("activeC");
                if (content) {
                    content.classList.toggle("invisible");
                    if (content.style.display === "block") {
                        content.style.display = "none";
                    } else {
                        content.style.display = "block";
                    }
                }
            };
        }
    })

    observer.observe(app, {
        subtree: true,
        attributes: true,
        childList: true,
        characterData: true
    })
}

/*
function TableSort(o,c){
    var rows = $('#table-chain tbody  tr').get();
    rows.sort(function(a, b) {

        var A = getVal(a);
        var B = getVal(b);

        if(A < B) {
            return -1*o;
        }
        if(A > B) {
            return 1*o;
        }
        return 0;
    });

    function getVal(elm){
        var v = $(elm).children('td').eq(c).text().toUpperCase();
        if($.isNumeric(v)){
            v = parseInt(v,10);
        }
        return v;
    }

    $.each(rows, function(index, row) {
        $('#table-chain').children('tbody').append(row);
    });

}

var o_name = 1; //
var o_num = 1; //

$("#name").onclick(function(){
    o_name *= -1; // toggles ascending/descending
    var n = $(this).prevAll().length;
    TableSort(o_name,n);
});
$("#num").onclick(function(){
    o_num *= -1; // toggles ascending/descending
    var n = $(this).prevAll().length;
    TableSort(o_num,n);
});
*/

// TODO: populate from blockchain
function searchfunction() {

}

function updateDownload(progress) {

}

function changePage(page) {
    react("change_page", page)
}

let observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (!mutation.addedNodes) return

        for (let i = 0; i < mutation.addedNodes.length; i++) {
            // do things to your newly added nodes here
            let node = mutation.addedNodes[i]
            if (node.id === "app") {
                observer.disconnect()
                callback()
                return
            }
        }
    })
})

observer.observe(document.body, {
    childList: true,
    subtree: true
})
