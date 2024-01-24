import React, { useEffect, useRef, useState } from "react";
import Header from "./Header";
import { checkValidate } from "../utils/validate";
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
} from "firebase/auth";
import { auth } from "../utils/firebase";
import { useDispatch } from "react-redux";
import { addUser, removeUser } from "../rtk/userSlice";
import { useNavigate } from "react-router-dom";

const Login = () => {
  const [issSingnin, setissSingnin] = useState(true);
  const [errorMessage, seterrorMessage] = useState(null);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  const name = useRef(null);
  const email = useRef(null);
  const password = useRef(null);

  const handleButtonClickform = (e) => {
    e.preventDefault();
    // console.log(email ,password);
    const message = checkValidate(email.current.value, password.current.value);
    seterrorMessage(message);

    if (message) return;

    if (!issSingnin) {
      // signup logic

      createUserWithEmailAndPassword(
        auth,
        email.current.value,
        password.current.value
      )
        .then((userCredential) => {
          // Signed up
          const user = userCredential.user;
          // ...
        })
        .catch((error) => {
          const errorCode = error.code;
          const errorMessage = error.message;
          console.log(errorMessage);
          // ..
        });
    } else {
      // signin logic
      signInWithEmailAndPassword(
        auth,
        email.current.value,
        password.current.value
      )
        .then((userCredential) => {
          // Signed in
          const user = userCredential.user;
          // ...
        })
        .catch((error) => {
          const errorCode = error.code;
          const errorMessage = error.message;
          seterrorMessage(errorMessage);
        });
    }
  };

  useEffect(() => {
    onAuthStateChanged(auth, (user) => {
      if (user) {
        const { uid, email, displayName } = user;
        navigate("/browse");

        dispatch(addUser({ uid: uid, email: email, displayName: displayName }));
      } else {
        dispatch(removeUser());
        navigate("/");
      }
    });
  }, []);

  const handleSignupSignInToggle = () => {
    setissSingnin(!issSingnin);
  };

  return (
    <div className="  h-full">
      <Header />
      <div className="absolute">
        <img
          className="h-[80vh] object-cover lg:h-full"
          src="https://assets.nflxext.com/ffe/siteui/vlv3/16006346-87f9-4226-bc25-a1fb346a2b0c/9662d0fd-0547-4665-b887-771617268815/IN-en-20240115-popsignuptwoweeks-perspective_alpha_website_medium.jpg"
          alt="bgimge"
        />
      </div>

      <form className="p-10 bg-black absolute lg:mt-20 lg:h-auto   m-auto right-0 left-0 h-[100%]  bg-opacity-90 lg:w-3/12 text-white rounded-lg">
        <h1 className="font-bold text-3xl py-4 mt-6">
          {issSingnin ? "Sign In" : "Sign up"}{" "}
        </h1>
        {!issSingnin && (
          <input
            ref={name}
            type="text"
            placeholder="name"
            className="my-2 py-2 px-3 w-full bg-gray-700 rounded-md  "
          />
        )}

        <input
          ref={email}
          type="text"
          placeholder="email"
          className="my-2 py-2 px-3 w-full bg-gray-700 rounded-md  "
        />

        <input
          ref={password}
          type="password"
          className="my-2 py-2 w-full bg-gray-700  px-3 rounded-md"
          placeholder="password"
        />
        <p className="text-red-500 py-2 font-bold text-sm">{errorMessage}</p>

        <button
          type="submit"
          onClick={handleButtonClickform}
          className="px-4 py-3 my-2 w-full bg-red-700 rounded-lg "
        >
          {issSingnin ? "Sign in " : " Sign up  "}
        </button>

        <h2 onClick={handleSignupSignInToggle} className="text-sm py-2">
          {issSingnin ? "New to NetFlix" : "already a user"}{" "}
          <span className="font-semibold ml-2 cursor-pointer">
            {issSingnin ? "sigup now" : "sign in "}
          </span>{" "}
        </h2>
      </form>
    </div>
  );
};

export default Login;
