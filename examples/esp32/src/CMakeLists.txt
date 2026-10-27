# The firmware's own sources and the export's model files, copied into model/
# (docs/route/3-onto-a-board.md).
file(GLOB CARAVAN_SOURCES "*.cc" "model/*.cc")
idf_component_register(
    SRCS ${CARAVAN_SOURCES}
    INCLUDE_DIRS "." "model"
    PRIV_REQUIRES esp_system
)
