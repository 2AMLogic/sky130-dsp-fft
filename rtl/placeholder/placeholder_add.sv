// PLACEHOLDER: flow-bring-up module only. Not part of the FFT/FIR design and
// to be replaced by generated RTL (see verification/README.md).
//
// Registered adder with a valid/ready handshake on both sides. One result
// register; accepts a new operand pair whenever it is empty or being drained.
module placeholder_add #(
    parameter int unsigned WIDTH = 8
) (
    input  logic             clk,
    input  logic             rst_n,
    input  logic             in_valid,
    output logic             in_ready,
    input  logic [WIDTH-1:0] a,
    input  logic [WIDTH-1:0] b,
    output logic             out_valid,
    input  logic             out_ready,
    output logic [WIDTH:0]   sum
);

  assign in_ready = !out_valid || out_ready;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      out_valid <= 1'b0;
      sum       <= '0;
    end else begin
      if (in_ready) begin
        out_valid <= in_valid;
        if (in_valid) sum <= {1'b0, a} + {1'b0, b};
      end
    end
  end

endmodule
