SUMMARY = "Expande el rootfs al primer boot para usar toda la SD/eMMC"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://expand-rootfs.sh \
    file://expand-rootfs.service \
"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

inherit systemd

SYSTEMD_SERVICE:${PN} = "expand-rootfs.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

RDEPENDS:${PN} = "e2fsprogs-resize2fs parted util-linux-fdisk"

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${WORKDIR}/expand-rootfs.sh ${D}${sbindir}/expand-rootfs.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/expand-rootfs.service \
        ${D}${systemd_system_unitdir}/expand-rootfs.service
}

FILES:${PN} += " \
    ${sbindir}/expand-rootfs.sh \
    ${systemd_system_unitdir}/expand-rootfs.service \
"
