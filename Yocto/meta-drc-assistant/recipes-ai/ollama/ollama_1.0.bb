SUMMARY = "Ollama LLM runtime + Phi4 Mini model (offline)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://ollama-linux-arm64.tar.zst \
    file://phi4-mini-prebaked.tar.gz;unpack=0 \
    file://ollama.service \
"

do_configure[noexec] = "1"
do_compile[noexec] = "1"

S = "${WORKDIR}"

inherit systemd

SYSTEMD_SERVICE:${PN} = "ollama.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

# Binarios pre-compilados, deshabilitar QA checks de strip
INSANE_SKIP:${PN} = "already-stripped dev-so file-rdeps"
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_SYSROOT_STRIP = "1"
ERROR_QA:remove = "host-user-contaminated"
WARN_QA:remove = "host-user-contaminated"

do_install() {
    # Binario de Ollama (viene en bin/ollama dentro del tar)
    install -d ${D}${bindir}
    install -m 0755 ${WORKDIR}/bin/ollama ${D}${bindir}/ollama

    # Librerías de Ollama
    install -d ${D}${libdir}/ollama
    cp -r ${WORKDIR}/lib/ollama/ ${D}${libdir}/

    # Modelos pre-horneados — forzar ownership a root:root
    install -d ${D}/opt/ollama/models
    tar -xzf ${WORKDIR}/phi4-mini-prebaked.tar.gz \
        --no-same-owner \
        --no-same-permissions \
        -C ${D}/opt/ollama/models
    chown -R root:root ${D}/opt/ollama/models

    # Servicio systemd
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/ollama.service \
        ${D}${systemd_system_unitdir}/ollama.service
}

FILES:${PN} += " \
    ${bindir}/ollama \
    ${libdir}/ollama \
    /opt/ollama/models \
    ${systemd_system_unitdir}/ollama.service \
"
