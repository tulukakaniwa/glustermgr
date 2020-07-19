import json
from typing import Optional

from flask import Flask, render_template, request, jsonify, abort, url_for
from gluster import cli
import socket

app = Flask(__name__)
myhostname = socket.getfqdn()
myaddress = socket.gethostbyname(myhostname)


def b2u8(b: bytes) -> str:
    '''
    Convert result bytes to UTF-8 string
    :param bytes b: Input result bytes
    :rtype: str
    :return: UTF-8 string
    '''
    return b.decode("UTF-8")


def mkerrmsg(e: cli.GlusterCmdException):
    emsg = ""
    for earg in e.args:
        emsg += "gluster-cli: " + earg[1].decode("UTF-8").rstrip("\n") + (
            (': ' + earg[2].decode("UTF-8")).rstrip("\n") if len(earg[2]) > 0 else '') + " (%d)" % earg[0]
    return emsg


def render_status_page(operation_name: str, overall_status: str, module_status: str, status_message: str,
                       return_url: Optional[str] = None, return_btn_text: str = "Back",
                       module_status_color: str = 'black'):
    return render_template("statushow.html", operation=operation_name, status=overall_status, result=module_status,
                           message=status_message, return_url=return_url, return_btn_text=return_btn_text,
                           result_txt_color=module_status_color, myhostname=myhostname, myaddress=myaddress)


def render_gluster_exception(operation_name: str, module_status: str, exception: cli.GlusterCmdException,
                             return_url: Optional[str] = None, return_btn_text: str = "Back"):
    return render_status_page(operation_name, "Failed", module_status, mkerrmsg(exception), return_url,
                              module_status_color="red", return_btn_text=return_btn_text)


def get_peer_lists(by_uuid: bool = False, including_localhost=False):
    peers = list()
    if including_localhost:
        peerinfo = cli.peer.pool()
    else:
        peerinfo = cli.peer.status()
    for peer in peerinfo:
        peers.append(peer["uuid"] if by_uuid else peer["hostname"])
    return peers


def get_peer_status(peername: str) -> dict:
    '''
    Get peer status by using peer name.

    Will raise **GlusterCmdException** when failed to get peers.
    Will raise **KeyError** when no such peer.

    :param str peername: Peer name to be located
    :rtype: dict
    :return: Peer information dict (uuid, hostname, connected)
    '''
    peers = cli.peer.status()
    for peer in peers:
        if peer["hostname"] == peername:
            return peer
    raise KeyError(peername)


def get_volume_status(volname: str) -> dict:
    '''
    Get volume status by using peer name.

    Will raise **GlusterCmdException** when failed to get volumes.
    Will raise **KeyError** when no such volume.

    :param str volname: Volume name to be located
    :rtype: dict
    :return: volume information dict
    '''
    volumes = cli.volume.status_detail()
    for vol in volumes:
        if vol["name"] == volname:
            return vol
    raise KeyError(volname)


@app.route('/')
def main_menu():
    exception_msg = None
    try:
        peers = cli.peer.status()
        volumes = cli.volume.status_detail()
    except cli.GlusterCmdException as e:
        volumes = []
        peers = []
        exception_msg = mkerrmsg(e)
    return render_template("mainmenu.html", volumes=volumes, peers=peers,
                           myhostname=myhostname, myaddress=myaddress, exceptionmsg=exception_msg)


@app.route("/volume/<string:volname>")
def volume_details(volname):
    operation_name = "Manage volume"
    try:
        volumeinfo = get_volume_status(volname)
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Volume lookup failed", e), 500
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Volume lookup failed", "No such volume: " + str(volname),
                                  url_for("main_menu"), module_status_color="red"), 404
    return render_template("volumeview.html", volumeinfo=volumeinfo, myhostname=myhostname, myaddress=myaddress)
    pass


@app.route("/peer/<string:peername>")
def peer_details(peername):
    operation_name = "Manage peer"
    try:
        peerinfo = get_peer_status(peername)
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Peer lookup failed", e), 500
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Peer lookup failed", "No such peer: " + str(peername),
                                  url_for("main_menu"), module_status_color="red"), 404

    return render_template("peerview.html", peerinfo=peerinfo, myhostname=myhostname, myaddress=myaddress)
    pass


@app.route("/probe_peer")
def showpage_probe_peer():
    return render_template("newpeer.html", myhostname=myhostname, myaddress=myaddress)
    pass


@app.route("/create_volume")
def showpage_create_volume():
    peerlist = get_peer_lists(including_localhost=True)
    return render_template("newvolume.html", peerlist=peerlist, myhostname=myhostname, myaddress=myaddress)
    pass


@app.route("/volume/<string:volname>/add_brick")
def showpage_volume_add_brick(volname):
    operation_name = "Add brick"
    peerlist = get_peer_lists(including_localhost=True)
    try:
        volinfo = get_volume_status(volname)
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Add brick failed", "No such volume: " + str(volname),
                                  url_for("main_menu"), module_status_color="red"), 404
    return render_template("addbrick.html", peerlist=peerlist, volname=volname, volumeinfo=volinfo,
                           myhostname=myhostname, myaddress=myaddress)
    pass


@app.route("/operation/do_peer_probe", methods=["POST"])
def do_probe_peer():
    operation_name = "Probe peer"
    try:
        peer_adress = request.form["peer_address"]
        if len(peer_adress) == 0:
            raise KeyError
    except KeyError as e:
        return render_status_page(operation_name, "Error", "Error", "No peer information were provided.",
                                  url_for("showpage_probe_peer"), module_status_color="red"), 400
    # do something
    try:
        result = b2u8(cli.peer.probe(peer_adress))
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Probe failed", e,
                                        return_url=url_for("showpage_probe_peer")), 500
    return render_status_page(operation_name, "Success", "Probe success", result, url_for("main_menu"),
                              return_btn_text="Main Menu", module_status_color="green")
    pass


@app.route("/operation/do_peer_detach/<string:peername>")
def do_detach_peer(peername: str):
    operation_name = "Detach peer"
    try:
        get_peer_status(peername)
        result = b2u8(cli.peer.detach(peername))
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Peer detach failed", e), 500
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Peer detach failed", "No such peer: " + str(peername),
                                  url_for("main_menu"), module_status_color="red"), 404
    return render_status_page(operation_name, "Success", "Peer detach success", result, url_for("main_menu"),
                              return_btn_text="Main Menu", module_status_color="green")


@app.route("/operation/do_create_volume", methods=["POST"])
def do_create_volume():
    operation_name = "Create volume"
    try:
        volume_name = str(request.form["volume_name"])
        # stripe = int(request.form["strip"])
        replica = int(request.form["replica"])
        arbiter = int(request.form["arbiter"]) if replica > 0 else None
        disperse = int(request.form["disperse"])
        disperse_data = int(request.form["disperse_data"])
        redundancy = int(request.form["redundancy"])
        transport_tcp = bool("transport_tcp" in request.form.keys())
        transport_rdma = bool("transport_rdma" in request.form.keys())
        force = bool("force" in request.form.keys())
        bricks = json.loads(request.form["bricks"])
        if len(volume_name) == 0:
            raise KeyError("volume_name")
        if not (transport_rdma or transport_tcp):
            raise KeyError("transport")
    except KeyError as e:
        return render_status_page(operation_name, "Error", "Error", "Invaild request for creating volume.",
                                  url_for("showpage_create_volume"), module_status_color="red"), 400

    # do something
    transport_mode = ("tcp" if transport_tcp else "") + ("," if transport_tcp and transport_rdma else "") + (
        "rdma" if transport_rdma else "")
    brick_list = list()
    for brick in bricks:
        if brick["fspath"][0] != "/":
            # invalid fspath
            return render_status_page(operation_name, "Error", "Error",
                                      "Invalid filesystem path for" + brick["peer"] + ": " + brick["fspath"],
                                      url_for("showpage_create_volume"), module_status_color="red"), 400
        if brick["peer"] == "localhost":
            peeraddr = myaddress
        else:
            peeraddr = brick["peer"]
        brick_list.append(peeraddr + ":" + brick["fspath"])

    try:
        if arbiter is None:
            result = b2u8(cli.volume.create(volume_name, brick_list, replica=replica, disperse=disperse,
                                            disperse_data=disperse_data,
                                            redundancy=redundancy, transport=transport_mode, force=force))
        else:
            result = b2u8(cli.volume.create(volume_name, brick_list, replica=replica, arbiter=arbiter,
                                            disperse=disperse,
                                            disperse_data=disperse_data,
                                            redundancy=redundancy, transport=transport_mode, force=force))
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Create volume failed", e,
                                        return_url=url_for("showpage_create_volume")), 500
    return render_status_page(operation_name, "Success", "Create volume ", result, url_for("main_menu"),
                              return_btn_text="Main Menu", module_status_color="green")
    pass


@app.route("/operation/do_delete_volume/<string:volname>")
def do_delete_volume(volname):
    operation_name = "Delete volume"
    try:
        get_volume_status(volname)
        result = b2u8(cli.volume.delete(volname))
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Delete volume failed", e), 500
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Delete volume failed",
                                  "No such volume: " + str(volname),
                                  url_for("main_menu"), module_status_color="red"), 404
    return render_status_page(operation_name, "Success", "Delete volume success", result, url_for("main_menu"),
                              return_btn_text="Main Menu", module_status_color="green")
    pass


@app.route("/operation/do_start_volume/<string:volname>")
def do_start_volume(volname):
    operation_name = "Start volume"
    try:
        get_volume_status(volname)
        result = b2u8(cli.volume.start(volname))
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Start volume failed", e), 500
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Start volume failed", "No such volume: " + str(volname),
                                  url_for("main_menu"), module_status_color="red"), 404
    return render_status_page(operation_name, "Started", "Start volume success", result,
                              url_for("volume_details", volname=volname),
                              return_btn_text="Back", module_status_color="green")
    pass


@app.route("/operation/do_stop_volume/<string:volname>")
def do_stop_volume(volname):
    operation_name = "Stop volume"
    try:
        get_volume_status(volname)
        result = b2u8(cli.volume.stop(volname))
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Stop volume failed", e), 500
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Stop volume failed", "No such volume: " + str(volname),
                                  url_for("main_menu"), module_status_color="red"), 404
    return render_status_page(operation_name, "Stopped", "Stop volume success", result,
                              url_for("volume_details", volname=volname),
                              return_btn_text="Back", module_status_color="green")
    pass


@app.route("/operation/do_add_brick/<string:volname>", methods=["POST"])
def do_add_brick(volname):
    operation_name = "Add brick"
    try:
        # stripe = int(request.form["strip"]) if int(request.form["strip"]) > 0 else None
        replica = int(request.form["replica"]) if int(request.form["replica"]) > 0 else None
        arbiter = int(request.form["arbiter"]) if "arbiter" in request.form.keys() else None

        force = bool("force" in request.form.keys())
        bricks = json.loads(request.form["bricks"])
    except KeyError as e:
        return render_status_page(operation_name, "Error", "Error", "Invaild request for adding brick to volume.",
                                  url_for("showpage_volume_add_brick", volname=volname), return_btn_text="Back",
                                  module_status_color="red"), 400

    try:
        volstat = get_volume_status(volname)
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Add brick failed", e), 500
    except KeyError as e:
        return render_status_page(operation_name, "Failed", "Add brick failed", "No such volume: " + str(volname),
                                  url_for("main_menu"), module_status_color="red"), 404
    # do something
    brick_list = list()
    for brick in bricks:
        if brick["fspath"][0] != "/":
            # invalid fspath
            return render_status_page(operation_name, "Error", "Error",
                                      "Invalid filesystem path for" + brick["peer"] + ": " + brick["fspath"],
                                      url_for("showpage_create_volume"), module_status_color="red"), 400
        if brick["peer"] == "localhost":
            peeraddr = myaddress
        else:
            peeraddr = brick["peer"]
        brick_list.append(peeraddr + ":" + brick["fspath"])

    # stripe = stripe + volstat["stripe"] if stripe is not None else None
    replica = replica + volstat["replica"] if replica is not None else None
    arbiter = arbiter + volstat["arbiter"] if replica is not None else None

    try:
        if arbiter is None:
            result = b2u8(cli.volume.bricks.add(volname=volname, bricks=brick_list, replica=replica, force=force))
        else:
            result = b2u8(
                cli.volume.bricks.add(volname=volname, bricks=brick_list, replica=replica, arbiter=arbiter,
                                      force=force))
    except cli.GlusterCmdException as e:
        return render_gluster_exception(operation_name, "Add brick failed", e,
                                        return_url=url_for("showpage_volume_add_brick", volname=volname)), 500
    return render_status_page(operation_name, "Success", "Probe success", result,
                              url_for("showpage_volume_add_brick", volname=volname),
                              return_btn_text="Back", module_status_color="green")
    pass


if __name__ == '__main__':
    app.run()
