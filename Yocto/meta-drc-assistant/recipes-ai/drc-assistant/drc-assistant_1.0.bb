SUMMARY = "DRC Assistant — imagen Docker + servicios systemd"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://drc-assistant-arm64.tar;unpack=0 \
    file://drc-assistant.service \
    file://drc-first-run.service \
    git://github.com/Kendarooo/Proyecto_2_Embebidos.git;protocol=https;branch=feature/new_text;destsuffix=git-repo \
    file://eth0.network \
"
SRCREV = "427c9794642941ab27c9046c99d848ef9e7cb51a"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

inherit systemd

SYSTEMD_SERVICE:${PN} = "drc-assistant.service drc-first-run.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

RDEPENDS:${PN} = "docker"

do_install() {
    # Imagen Docker
    install -d ${D}/opt/drc-assistant
    install -m 0644 ${WORKDIR}/drc-assistant-arm64.tar \
        ${D}/opt/drc-assistant/drc-assistant-arm64.tar

    # Directorios de datos persistentes (vacíos, se llenan en runtime)
    install -d ${D}/opt/drc-assistant/data/chroma_db
    install -d ${D}/opt/drc-assistant/logs

    # Corpus desde el git
    install -d ${D}/opt/drc-assistant/corpus/raw
    install -d ${D}/opt/drc-assistant/corpus/annotated
    install -m 0644 ${WORKDIR}/git-repo/corpus/raw/xh018-DR-v10_1_1.txt \
        ${D}/opt/drc-assistant/corpus/raw/
    install -m 0644 ${WORKDIR}/git-repo/corpus/raw/147464.pdf \
        ${D}/opt/drc-assistant/corpus/raw/
    install -m 0644 ${WORKDIR}/git-repo/corpus/annotated/nand2_drc_errors.json \
        ${D}/opt/drc-assistant/corpus/annotated/

    # Habilitar systemd-networkd
    install -d ${D}${sysconfdir}/systemd/system/multi-user.target.wants
    ln -sf /lib/systemd/system/systemd-networkd.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/systemd-networkd.service

    # Habilitar sshd en arranque
    ln -sf /lib/systemd/system/sshd.service \
        ${D}${sysconfdir}/systemd/system/multi-user.target.wants/sshd.service

    # Servicios systemd
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/drc-assistant.service \
        ${D}${systemd_system_unitdir}/drc-assistant.service
    install -m 0644 ${WORKDIR}/drc-first-run.service \
        ${D}${systemd_system_unitdir}/drc-first-run.service

    # Configuración de red estática
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${WORKDIR}/eth0.network \
        ${D}${sysconfdir}/systemd/network/eth0.network
}

FILES:${PN} += " \
    /opt/drc-assistant \
    ${systemd_system_unitdir}/drc-assistant.service \
    ${systemd_system_unitdir}/drc-first-run.service \
    ${sysconfdir}/systemd/network/eth0.network \
    ${sysconfdir}/systemd/system/multi-user.target.wants/sshd.service \
"
