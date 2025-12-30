#pragma once
#include <cstdint>

namespace dsp {

struct Phasor {
    int16_t phase = 0;


    int16_t tick(int16_t inc) {
        phase += inc;
        return phase;
    }
};

/// Single saw wave (Q16) [-32768..32767]
inline int32_t sawSample(uint16_t ph) {
    return ((int32_t)ph << 16) - 0x80000000;
}

/// Supersaw with N voices
template<int N>
struct Supersaw {
    Phasor phasors[N];
    int32_t detune[N];    // Q16 detune offsets

    Supersaw() {
        for (int i = 0; i < N; ++i) {
            detune[i] = 0;
        }
    }

    /// Initialize phasors
    void init() {
        for (int i = 0; i < N; ++i)
            phasors[i].phase = 0;
    }

    /// Initialize detune amounts (Q16 units)
    void initDetune(int32_t amount) {
        for (int i = 0; i < N; ++i) {
            int32_t factor = (i - N/2) * amount;
            detune[i] = factor;
        }
    }

    /// Set frequency for all voices
    void setFreq(float freq, float sampleRate) {
        for (int i = 0; i < N; ++i) {
            // Apply detune in Q16
            phasors[i].setFreq(freq + (detune[i] / 65536.0f), sampleRate);
        }
    }

    /// Return mono mix of all voices
    int32_t processMono() {
        int64_t sum = 0;
        for (int i = 0; i < N; ++i) {
            sum += sawSample(phasors[i].tick());
        }
        return (int32_t)(sum / N); // average
    }
};

} // namespace dsp
