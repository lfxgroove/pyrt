var xmlhttp;

function select_torrent(elem) {
    elem.style.backgroundColor = "#00CCFF";
    elem.style.cursor = "help";
}
function deselect_torrent(elem) {
    elem.style.backgroundColor = null;
    elem.style.cursor = "default";
}
function select_tab(elem) {
   elem.style.backgroundColor = "#37FDFC"; 
}

function deselect_tab(elem) {
    elem.style.backgroundColor = null;
}

function navigate_tab(elem) {
    window.location = "?view=" + elem.id.split("tab_")[1];
}

function navigate_torrent(elem) {
    window.location = "detail.py?torrent_id=" + elem.id.split("torrent_id_")[1]
}

function htmlify(json, cell) {
    var obj = JSON.parse(json);
    var new_html = new String();
    new_html += "<div class='drop_down'>"
    new_html += "<div class='column-1'>ID:</div><div class='column-2'>" + obj.torrent_id + "</div>"
    new_html += "<div class='column-1'>Size:</div><div class='column-2'>" + obj.size + "</div>"
    new_html += "<div class='column-1'>Downloaded:</div><div class='column-2'>" + obj.downloaded  + "</div>"
    new_html += "<div class='column-1'>Uploaded:</div><div class='column-2'>" + obj.uploaded + "</div>"
    new_html += "<div class='column-1'>Ratio:</div><div class='column-2'>" + obj.ratio + "</div>"
    new_html += "<div class='column-1'>Peers:</div><div class='column-2'>" + obj.peers.length + "</div>"
    new_html += "<div class='column-1'>Created:</div><div class='column-2'>" + obj.created + "</div>"
    new_html += "<div class='column-2' style='clear : left;'><span class='fakelink' onClick='removerow(\"" + obj.torrent_id + "\")'>Close</span> <a href='detail.py?torrent_id=" + obj.torrent_id + "'>Detailed View</a></div>"
    new_html += "</div>"
    cell.innerHTML = new_html;
    cell.style.borderLeft="1px dotted";
    cell.style.borderRight="1px dotted";
    cell.style.backgroundColor = "white";
}
function removerow(torrent_id) {
    if (row = document.getElementById("newrow_torrent_id_" + torrent_id)) {
        var table = document.getElementById("torrent_list");
        table.deleteRow(row.rowIndex);
    }
    
}
function view_torrent(elem) {
    var torrent_id = elem.id.split("torrent_id_")[1];
    var table = document.getElementById("torrent_list");
    if (oldrow = document.getElementById('newrow_torrent_id_' + torrent_id)) {
        table.deleteRow(oldrow.rowIndex);
    }
    var newrow = table.insertRow(elem.rowIndex + 1);
    var newcell = newrow.insertCell(0);
    newrow.id = "newrow_torrent_id_" + torrent_id;
    newcell.innerHTML = "<img src='../images/loading.gif'> <span style='color:red;'>Loading</span>";
    newcell.colSpan = "6";
    xmlhttp = new XMLHttpRequest();
    var url="ajax.py"
    xmlhttp.open("POST",url,true);
    xmlhttp.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xmlhttp.onreadystatechange = function () {
        if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
            var response = xmlhttp.responseText;
            // newcell.innerHTML = response;
            htmlify(response, newcell);
        }
    }
    var params = "request=get_torrent_info&torrent_id=" + torrent_id;
    xmlhttp.send(params);
}