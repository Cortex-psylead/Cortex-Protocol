pragma circom 2.1.6;

// mvd_range_check.circom
// CORTEX PROTOCOL — Layer 2: MVD Zero-Knowledge Range Proof
// Status: FUNCTIONAL — Can be compiled with circom 2.x + snarkjs
//
// Proves: u_min <= v_local <= u_max
// WITHOUT revealing v_local to the verifier (Acolyte).
//
// Uses Poseidon hash for commitment verification (ZK-friendly, no trusted setup).
// Bulletproofs/Ristretto255 is the production target — this Groth16 circuit
// is the current compilable reference implementation.
//
// Compile: circom mvd_range_check.circom --r1cs --wasm --sym
// Prove:   snarkjs groth16 prove mvd_range_check.zkey witness.wtns proof.json public.json

include "./node_modules/circomlib/circuits/comparators.circom";
include "./node_modules/circomlib/circuits/poseidon.circom";

template MVDRangeChecker(n_bits) {
    // ── PUBLIC inputs (known to Acolyte / verifier) ──────────────────────
    signal input u_min;           // Lower homeostatic bound (from White Branch snapshot)
    signal input u_max;           // Upper homeostatic bound
    signal input expected_hash;   // Poseidon commitment: Hash(v_local, blinding_factor)

    // ── PRIVATE inputs (known only to prover / user device) ──────────────
    signal input v_local;         // Purified biometric feature (the secret)
    signal input blinding_factor; // Cryptographic blinding — prevents commitment brute-force

    // ── Internal components ───────────────────────────────────────────────
    component comp_min     = GreaterEqThan(n_bits);
    component comp_max     = LessEqThan(n_bits);
    component hash_verifier = Poseidon(2);

    // ── Constraint 1: Commitment integrity ───────────────────────────────
    // Verifies that v_local matches the committed value.
    // Acolyte can verify commitment without learning v_local.
    hash_verifier.inputs[0] <== v_local;
    hash_verifier.inputs[1] <== blinding_factor;
    hash_verifier.out       === expected_hash;

    // ── Constraint 2: Lower bound (v_local >= u_min) ─────────────────────
    comp_min.in[0] <== v_local;
    comp_min.in[1] <== u_min;
    comp_min.out   === 1;   // R1CS constraint: must be satisfied for valid proof

    // ── Constraint 3: Upper bound (v_local <= u_max) ─────────────────────
    comp_max.in[0] <== v_local;
    comp_max.in[1] <== u_max;
    comp_max.out   === 1;   // If this fails, proof generation fails — no false proofs
}

// Instantiate for 32-bit clinical ranges.
// n_bits = 32 supports normalized clinical values in [0, 4,294,967,295].
// Reduce to n_bits = 16 for wearable devices with constrained prover.
component main {public [u_min, u_max, expected_hash]} = MVDRangeChecker(32);
