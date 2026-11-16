#pragma once

#include <Bamboo/Bamboo.hpp>
#include <Bamboo/Script.hpp>

#include <vector>

// A script with a published field of every type and a list of every kind of thing. It does one
// thing: when the game starts it logs what the world gave its fields — one line that begins with
// "PROBE". The UI tests of the editor set the fields in the inspector and read the line in Play
// and in the exported game: what was set is what the game got.
class Probe : public Bamboo::Script {
public:
    int count = 0;
    float speed = 0.f;
    Bamboo::EntityHandle target;
    Bamboo::TextureHandle icon;
    Bamboo::MaterialHandle skin;
    Bamboo::WorldHandle next;
    std::vector<int> numbers;
    std::vector<Bamboo::WorldHandle> levels;
    std::vector<Bamboo::TextureHandle> frames;
    std::vector<Bamboo::EntityHandle> waypoints;

    PANDA_FIELDS_BEGIN(Probe)
    PANDA_FIELD(count)
    PANDA_FIELD(speed)
    PANDA_FIELD(target)
    PANDA_FIELD(icon)
    PANDA_FIELD(skin)
    PANDA_FIELD(next)
    PANDA_FIELD(numbers)
    PANDA_FIELD(levels)
    PANDA_FIELD(frames)
    PANDA_FIELD(waypoints)
    PANDA_FIELDS_END

    void start() override;
};

REGISTER_SCRIPT(Probe)
