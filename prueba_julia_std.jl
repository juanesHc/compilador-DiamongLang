
# Código Julia generado por DiamondLang Compiler v4.0
# Fecha de generación: 2026-05-31T16:01:22

function principal()
    a::Int = 10
    b::Int = 3
    division_entera::Int = a ÷ b
    println(division_entera)
    x::Float64 = 10.0
    b_real::Float64 = 3.0
    division_real::Float64 = x / b_real
    println(division_real)
    mezcla::Float64 = a / b_real
    println(mezcla)
end

principal()

