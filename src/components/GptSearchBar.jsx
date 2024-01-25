import React from "react";
import lang from "../utils/languageConstant";
import { useSelector } from "react-redux";

const GptSearchBar = () => {
  const langDetails = useSelector((store) => store.config.lang);

  return (
    <div className="pt-[30%] lg:pt-[15%] lg:flex lg:items-center lg:justify-center">
      <form className="bg-black lg:w-[60%]  ">
        <input
          type="text"
          className="py-2 px-4 w-[80%]  lg:w-[85%] m-2 rounded-lg "
          placeholder={lang[langDetails].gptSearchPlaceholder}
        />
        <button className="py-2 px-2 bg-red-500 text-white rounded-lg">
          {lang[langDetails].search}
        </button>
      </form>
    </div>
  );
};

export default GptSearchBar;
