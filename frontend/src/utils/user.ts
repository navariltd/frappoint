export interface SignUp {
  first_name: string;
  last_name: string;
  email: string;
  gender: string;
  phone: string;
  password: string;
}

export const initialForm: SignUp = {
  first_name: "",
  last_name: "",
  email: "",
  gender: "",
  phone: "",
  password: ""
};

export function resetSignUpForm(form: SignUp) {
  form.first_name = "";
  form.last_name = "";
  form.email = "";
  form.gender = "";
  form.phone = "";
}


export function validatePasswordMatch(password1: string, password2: string) {
    if (!password1 || !password2) {
        throw new Error("Please enter both password fields")
    }
    if (password1 !== password2) {
        throw new Error("Password mismatch!")
    }

    if (password1.length < 8) {
        throw new Error("Password must be atleast 8 characters long!")
    }
}

export function isValidPhone(phone: string) {
  const internationalRegex = /^\+254\d{9}$/;
  const nationalRegex = /^0[71]\d{8}$/;

  return internationalRegex.test(phone) || nationalRegex.test(phone);
}

export function validatePhoneNumber(phone: string) {
    if (!isValidPhone(phone)) {
        throw new Error("Invalid phone number!")
    }
}
