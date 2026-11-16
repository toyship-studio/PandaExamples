#include "Probe.hpp"

#include <Bamboo/Logger.hpp>

#include <string>

namespace {

template<typename Item, typename Id>
std::string listOf(const std::vector<Item> &items, Id id) {
    std::string text = "[";
    for (size_t i = 0; i < items.size(); ++i) {
        if (i > 0) { text += ","; }
        text += std::to_string(id(items[i]));
    }
    return text + "]";
}

} // namespace

void Probe::start() {
    const std::string line =
        "PROBE count=" + std::to_string(count) + " speed=" + std::to_string(speed) + " target=" + std::to_string(target.id) +
        " icon=" + std::to_string(icon.id()) + " skin=" + std::to_string(skin.id()) + " next=" + std::to_string(next.id()) +
        " numbers=" + listOf(numbers, [](int value) { return value; }) +
        " levels=" + listOf(levels, [](const Bamboo::WorldHandle &world) { return world.id(); }) +
        " frames=" + listOf(frames, [](const Bamboo::TextureHandle &texture) { return texture.id(); }) +
        " waypoints=" + listOf(waypoints, [](const Bamboo::EntityHandle &entity) { return entity.id; });
    LOG_INFO("%s", line.c_str());
}
