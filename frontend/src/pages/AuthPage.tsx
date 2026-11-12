import { zodResolver } from "@hookform/resolvers/zod";
import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useAuth } from "@/context/AuthContext";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});
export const registerSchema = loginSchema.extend({
  full_name: z.string().trim().min(1, "Your name is required").max(200),
  password: z.string().min(8, "Use at least 8 characters"),
  hospital_name: z.string().trim().min(1, "Hospital name is required").max(200),
  hospital_city: z.string().optional(),
});

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const isLogin = mode === "login";
  const { user, login, register: signUp } = useAuth();
  const navigate = useNavigate();
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(isLogin ? loginSchema : registerSchema) as never,
  });

  if (user) return <Navigate to="/" replace />;

  const onSubmit = handleSubmit(async (v) => {
    setServerError(null);
    try {
      if (isLogin) await login(v.email, v.password);
      else await signUp(v.email, v.full_name, v.password, v.hospital_name, v.hospital_city);
      navigate("/", { replace: true });
    } catch (e) {
      setServerError(e instanceof Error ? e.message : "Something went wrong");
    }
  });

  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-white"><ShieldCheck size={18} /></span>
          <span className="text-lg font-semibold tracking-tight">InsureMate AI</span>
        </div>
        <h1 className="text-xl font-semibold tracking-tight">{isLogin ? "Sign in" : "Register your hospital"}</h1>
        <p className="mt-1 text-sm text-muted">{isLogin ? "Hospital insurance desk: patient policies, claim clearance and eligibility." : "Your hospital's data stays private to this account."}</p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
          {!isLogin && <Field label="Hospital name" autoComplete="organization" error={errors.hospital_name?.message} {...register("hospital_name")} />}
          {!isLogin && <Field label="City (optional)" {...register("hospital_city")} />}
          {!isLogin && <Field label="Your name" autoComplete="name" error={errors.full_name?.message} {...register("full_name")} />}
          <Field label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
          <Field label="Password" type="password" autoComplete={isLogin ? "current-password" : "new-password"} error={errors.password?.message} {...register("password")} />
          {serverError && <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{serverError}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting ? "Please wait…" : isLogin ? "Sign in" : "Register hospital"}</Button>
        </form>
        <p className="mt-6 text-sm text-muted">
          {isLogin ? "New here? " : "Already registered? "}
          <Link to={isLogin ? "/register" : "/login"} className="font-medium text-primary hover:underline">{isLogin ? "Register your hospital" : "Sign in"}</Link>
        </p>
      </div>
    </div>
  );
}
