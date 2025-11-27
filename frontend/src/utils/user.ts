export interface SignUp {
  first_name: string;
  last_name: string;
  email: string;
  gender: string;
  phone: string;
}

export const initialForm: SignUp = {
  first_name: "",
  last_name: "",
  email: "",
  gender: "",
  phone: "",
};

export function resetSignUpForm(form: SignUp) {
  form.first_name = "";
  form.last_name = "";
  form.email = "";
  form.gender = "";
  form.phone = "";
}
